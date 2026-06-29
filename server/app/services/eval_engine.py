"""评估引擎：真加载一个模型版本，在已发布测试集上跑推理、算指标、落库。

- 复用推理 worker（services/inference.py）执行确定性生成（temperature=0）；
- 指标由 metrics_compute 计算（文本级 P/R/F1 + 完全匹配 + 实体级各类别 + 错误案例）；
- 结果写入评估表（按模型类型覆盖 eval_metric / eval_per_class / error_case，新增 eval_task），
  并回写 model_version.f1 + status，把「微调出的模型」与评估真实串起来；
- 后台线程执行，进度存内存，前端轮询 /evaluation/run/{id}。
"""
import random
import threading
from datetime import datetime

from sqlalchemy import delete as sa_delete

from app.core import storage as st
from app.core.config import settings
from app.core.database import SessionLocal
from app.crud import dataset as ds_crud
from app.models.dataset import Dataset
from app.models.evaluation import (
    EvalTask, EvalMetric, EvalPerClass, ErrorCase, BenchmarkResult, SceneCase, ReviewSample,
)
from app.models.model_version import ModelVersion
from app.models.task import TrainTask
from app.services import metrics_compute as mc
from app.services.inference import manager as infer

DEFAULT_LIMIT = 50
EVAL_CAP = 300


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class EvalRunner:
    def __init__(self):
        self._lock = threading.Lock()
        self._runs: dict[int, dict] = {}   # eval_task_id -> {status,done,total,error}

    def start(self, model_id: str, dataset_id: int, limit: int, creator: str) -> dict:
        """创建评估任务并起后台线程。返回 {evalTaskId, modelType}。"""
        limit = max(1, min(int(limit or DEFAULT_LIMIT), EVAL_CAP))
        db = SessionLocal()
        try:
            label, model_type = self._model_label_type(db, model_id)
            ds = db.get(Dataset, dataset_id)
            if not ds:
                raise ValueError("测试集不存在")
            if ds.stage != "已发布":
                raise ValueError("测试集需为「已发布」数据集")
            et = EvalTask(model=label, modelType=model_type, dataset=ds.name,
                          status="评估中", evalAt=_now())
            db.add(et)
            db.commit()
            db.refresh(et)
            eid = et.id
        finally:
            db.close()
        with self._lock:
            self._runs[eid] = {"status": "评估中", "done": 0, "total": 0, "error": ""}
        threading.Thread(target=self._run, args=(eid, model_id, dataset_id, limit,
                                                 model_type, label), daemon=True).start()
        return {"evalTaskId": eid, "modelType": model_type}

    def status(self, db, eid: int) -> dict | None:
        et = db.get(EvalTask, eid)
        if not et:
            return None
        with self._lock:
            mem = dict(self._runs.get(eid, {}))
        return {
            "evalTaskId": eid, "status": mem.get("status", et.status),
            "done": mem.get("done", 0), "total": mem.get("total", 0),
            "error": mem.get("error", ""), "modelType": et.modelType,
            "f1": et.f1, "precision": et.precision, "recall": et.recall,
            "model": et.model, "dataset": et.dataset,
        }

    # ---- 内部 ----
    def _model_label_type(self, db, model_id: str) -> tuple[str, str]:
        if model_id.startswith("mv:"):
            mv = db.get(ModelVersion, int(model_id[3:]))
            if not mv:
                raise ValueError("模型版本不存在")
            return f"{mv.name} {mv.version or ''}".strip(), mc.norm_model_type(mv.modelType)
        if model_id.startswith("base:"):
            name = model_id[5:]
            # 基座无业务类型，按测试集类型归一（评估页据此展示）
            return f"{name}（基座）", ""
        raise ValueError(f"无法识别的模型标识: {model_id}")

    def _set(self, eid: int, **kw):
        with self._lock:
            self._runs.setdefault(eid, {}).update(kw)

    def _run(self, eid, model_id, dataset_id, limit, model_type, label):
        db = SessionLocal()
        try:
            ds = db.get(Dataset, dataset_id)
            if not model_type:   # 基座模型：用测试集类型作为指标归类
                model_type = mc.norm_model_type(ds.type)
            rec = ds_crud.dataset_file_for_task(db, ds.id, model_type, split="test")
            if not rec:
                raise ValueError("测试集没有可用的已发布训练文件")
            rows = mc.load_alpaca(st.abspath_of("datasets", rec.storedName))
            if not rows:
                raise ValueError("测试集为空或无法解析")
            random.seed(42)
            if len(rows) > limit:
                rows = random.sample(rows, limit)
            self._set(eid, total=len(rows))

            triples, _lat = self._infer_rows(db, eid, model_id, rows)
            result = mc.evaluate(triples, model_type)
            self._persist(db, eid, model_id, model_type, result)
            self._set(eid, status="已完成")
        except Exception as e:
            self._set(eid, status="失败", error=str(e))
            try:
                et = db.get(EvalTask, eid)
                if et:
                    et.status = "失败"
                    db.commit()
            except Exception:
                db.rollback()
        finally:
            db.close()

    def _infer_rows(self, db, eid, model_id, rows, base_done=0):
        """对每条样本跑一次确定性生成，返回 (triples, 平均耗时秒)。done 从 base_done 起累加。"""
        triples = []
        elapsed_sum = 0.0
        for i, r in enumerate(rows):
            instr = (r.get("instruction") or "").strip()
            inp = (r.get("input") or "").strip()
            gold = r.get("output") or ""
            prompt = instr if not inp else f"{instr}\n{inp}"
            res = infer.chat(db, model_id, [{"role": "user", "content": prompt}],
                             {"maxTokens": 512, "temperature": 0.0})
            triples.append((prompt, gold, res.get("reply", "")))
            elapsed_sum += float(res.get("elapsed") or 0)
            self._set(eid, done=base_done + i + 1)
        avg = round(elapsed_sum / len(rows), 3) if rows else 0
        return triples, avg

    # ---- 基准对比：微调模型 vs 基座模型，同一测试集 ----
    def start_benchmark(self, model_id: str, dataset_id: int, limit: int, creator: str) -> dict:
        limit = max(1, min(int(limit or DEFAULT_LIMIT), EVAL_CAP))
        db = SessionLocal()
        try:
            if not model_id.startswith("mv:"):
                raise ValueError("基准对比需选择一个微调版本")
            label, model_type = self._model_label_type(db, model_id)
            mv = db.get(ModelVersion, int(model_id[3:]))
            t = db.get(TrainTask, mv.task_id) if (mv and mv.task_id) else None
            base_name = (t.baseModel if t else "") or ""
            if not base_name:
                raise ValueError("该版本未记录基座模型，无法对比")
            ds = db.get(Dataset, dataset_id)
            if not ds:
                raise ValueError("测试集不存在")
            if ds.stage != "已发布":
                raise ValueError("测试集需为「已发布」数据集")
            et = EvalTask(model=f"{label} vs {base_name}（基座）", modelType=model_type,
                          dataset=ds.name, status="评估中", evalAt=_now())
            db.add(et)
            db.commit()
            db.refresh(et)
            eid = et.id
        finally:
            db.close()
        with self._lock:
            self._runs[eid] = {"status": "评估中", "done": 0, "total": 0, "error": ""}
        threading.Thread(target=self._run_benchmark,
                         args=(eid, model_id, f"base:{base_name}", dataset_id, limit, model_type),
                         daemon=True).start()
        return {"benchRunId": eid, "modelType": model_type}

    def _run_benchmark(self, eid, model_id, base_id, dataset_id, limit, model_type):
        db = SessionLocal()
        try:
            ds = db.get(Dataset, dataset_id)
            if not model_type:
                model_type = mc.norm_model_type(ds.type)
            rec = ds_crud.dataset_file_for_task(db, ds.id, model_type, split="test")
            if not rec:
                raise ValueError("测试集没有可用的已发布训练文件")
            rows = mc.load_alpaca(st.abspath_of("datasets", rec.storedName))
            if not rows:
                raise ValueError("测试集为空或无法解析")
            random.seed(42)
            if len(rows) > limit:
                rows = random.sample(rows, limit)
            self._set(eid, total=2 * len(rows))

            ft_tr, ft_lat = self._infer_rows(db, eid, model_id, rows, base_done=0)
            base_tr, base_lat = self._infer_rows(db, eid, base_id, rows, base_done=len(rows))
            ft = mc.evaluate(ft_tr, model_type)
            base = mc.evaluate(base_tr, model_type)
            self._persist_benchmark(db, ft, base, ft_lat, base_lat)
            et = db.get(EvalTask, eid)
            if et:
                et.f1, et.precision, et.recall = ft["f1"], ft["precision"], ft["recall"]
                et.status = "已完成"
                db.commit()
            self._set(eid, status="已完成")
        except Exception as e:
            self._set(eid, status="失败", error=str(e))
            try:
                et = db.get(EvalTask, eid)
                if et:
                    et.status = "失败"
                    db.commit()
            except Exception:
                db.rollback()
        finally:
            db.close()

    def _persist_benchmark(self, db, ft, base, ft_lat, base_lat):
        """落 benchmark_result：current=微调模型，prod=基座模型；推理速度为相对分（快者 100）。"""
        def speed(lat, other):
            cands = [x for x in (lat, other) if x and x > 0]
            return round(min(cands) / lat * 100, 1) if (cands and lat and lat > 0) else 0
        dims = [
            ("精确率", ft["precision"] * 100, base["precision"] * 100),
            ("召回率", ft["recall"] * 100, base["recall"] * 100),
            ("F1 值", ft["f1"] * 100, base["f1"] * 100),
            ("完全匹配率", ft["exactRate"] * 100, base["exactRate"] * 100),
            ("推理速度", speed(ft_lat, base_lat), speed(base_lat, ft_lat)),
        ]
        db.execute(sa_delete(BenchmarkResult))
        for i, (dim, cur, prod) in enumerate(dims):
            db.add(BenchmarkResult(dim=dim, current=round(cur, 1), prod=round(prod, 1),
                                   hist=None, seq=i))
        db.commit()

    # ---- 真实业务场景验证：一个模型在多个已发布测试集上各跑一遍 ----
    def start_scene(self, model_id: str, dataset_ids: list[int], limit: int, creator: str) -> dict:
        limit = max(1, min(int(limit or DEFAULT_LIMIT), EVAL_CAP))
        db = SessionLocal()
        try:
            label, model_type = self._model_label_type(db, model_id)
            ids = [int(x) for x in (dataset_ids or [])]
            if not ids:
                raise ValueError("请至少选择一个测试集作为业务场景")
            names = []
            for did in ids:
                ds = db.get(Dataset, did)
                if not ds:
                    raise ValueError(f"数据集 {did} 不存在")
                if ds.stage != "已发布":
                    raise ValueError(f"数据集「{ds.name}」需为「已发布」")
                names.append(ds.name)
            et = EvalTask(model=label, modelType=model_type or "",
                          dataset="、".join(names)[:128], status="评估中", evalAt=_now())
            db.add(et)
            db.commit()
            db.refresh(et)
            eid = et.id
        finally:
            db.close()
        with self._lock:
            self._runs[eid] = {"status": "评估中", "done": 0, "total": 0, "error": ""}
        threading.Thread(target=self._run_scene,
                         args=(eid, model_id, ids, limit, model_type), daemon=True).start()
        return {"sceneRunId": eid, "modelType": model_type}

    def _run_scene(self, eid, model_id, dataset_ids, limit, model_type):
        db = SessionLocal()
        try:
            jobs = []   # (dataset, model_type, rows)
            for did in dataset_ids:
                ds = db.get(Dataset, did)
                if not ds:
                    continue
                mt = model_type or mc.norm_model_type(ds.type)
                rec = ds_crud.dataset_file_for_task(db, ds.id, mt, split="test")
                if not rec:
                    continue
                rows = mc.load_alpaca(st.abspath_of("datasets", rec.storedName))
                if not rows:
                    continue
                random.seed(42)
                if len(rows) > limit:
                    rows = random.sample(rows, limit)
                jobs.append((ds, mt, rows))
            if not jobs:
                raise ValueError("所选测试集均无可用的已发布训练文件")
            self._set(eid, total=sum(len(r) for _, _, r in jobs))

            done = 0
            cases = []
            for ds, mt, rows in jobs:
                triples, _lat = self._infer_rows(db, eid, model_id, rows, base_done=done)
                done += len(rows)
                res = mc.evaluate(triples, mt)
                acc = round(res["f1"] * 100, 1)
                cases.append({"caseNo": ds.name, "type": ds.type, "sampleCount": len(rows),
                              "accuracy": acc, "hard": acc < 90.0})

            self._persist_scene(db, cases)
            et = db.get(EvalTask, eid)
            if et:
                et.status = "已完成"
                et.f1 = round(sum(c["accuracy"] for c in cases) / len(cases) / 100, 4)
                db.commit()
            self._set(eid, status="已完成")
        except Exception as e:
            self._set(eid, status="失败", error=str(e))
            try:
                et = db.get(EvalTask, eid)
                if et:
                    et.status = "失败"
                    db.commit()
            except Exception:
                db.rollback()
        finally:
            db.close()

    def _persist_scene(self, db, cases: list[dict]):
        db.execute(sa_delete(SceneCase))
        for c in cases:
            db.add(SceneCase(caseNo=c["caseNo"], type=c["type"], sampleCount=c["sampleCount"],
                             accuracy=c["accuracy"], hard=c["hard"]))
        db.commit()

    # ---- 人工复核抽样：真模型预测入复核队列（待复核）----
    def start_review(self, model_id: str, dataset_id: int, count: int,
                     reviewer: str, creator: str) -> dict:
        count = max(1, min(int(count or 10), EVAL_CAP))
        db = SessionLocal()
        try:
            label, model_type = self._model_label_type(db, model_id)
            ds = db.get(Dataset, dataset_id)
            if not ds:
                raise ValueError("测试集不存在")
            if ds.stage != "已发布":
                raise ValueError("测试集需为「已发布」数据集")
            et = EvalTask(model=label, modelType=model_type or "", dataset=ds.name,
                          status="评估中", evalAt=_now())
            db.add(et)
            db.commit()
            db.refresh(et)
            eid = et.id
        finally:
            db.close()
        with self._lock:
            self._runs[eid] = {"status": "评估中", "done": 0, "total": 0, "error": ""}
        threading.Thread(target=self._run_review,
                         args=(eid, model_id, dataset_id, count, reviewer, model_type),
                         daemon=True).start()
        return {"reviewRunId": eid, "modelType": model_type}

    def _run_review(self, eid, model_id, dataset_id, count, reviewer, model_type):
        db = SessionLocal()
        try:
            ds = db.get(Dataset, dataset_id)
            mt = model_type or mc.norm_model_type(ds.type)
            rec = ds_crud.dataset_file_for_task(db, ds.id, mt, split="test")
            if not rec:
                raise ValueError("测试集没有可用的已发布训练文件")
            rows = mc.load_alpaca(st.abspath_of("datasets", rec.storedName))
            if not rows:
                raise ValueError("测试集为空或无法解析")
            random.seed(42)
            if len(rows) > count:
                rows = random.sample(rows, count)
            self._set(eid, total=len(rows))

            for i, r in enumerate(rows):
                instr = (r.get("instruction") or "").strip()
                inp = (r.get("input") or "").strip()
                prompt = instr if not inp else f"{instr}\n{inp}"
                res = infer.chat(db, model_id, [{"role": "user", "content": prompt}],
                                 {"maxTokens": 512, "temperature": 0.0})
                db.add(ReviewSample(content=prompt[:512],
                                    modelOutput=(res.get("reply", "") or "")[:512],
                                    reviewer=reviewer or "待分配", result="待复核",
                                    reviewedAt=None))
                db.commit()
                self._set(eid, done=i + 1)

            et = db.get(EvalTask, eid)
            if et:
                et.status = "已完成"
                db.commit()
            self._set(eid, status="已完成")
        except Exception as e:
            self._set(eid, status="失败", error=str(e))
            try:
                et = db.get(EvalTask, eid)
                if et:
                    et.status = "失败"
                    db.commit()
            except Exception:
                db.rollback()
        finally:
            db.close()

    def _persist(self, db, eid, model_id, model_type, result):
        # 自动化指标卡（按类型覆盖）
        db.execute(sa_delete(EvalMetric).where(EvalMetric.modelType == model_type))
        for i, (name, val, unit) in enumerate(result["metrics"]):
            db.add(EvalMetric(modelType=model_type, name=name, value=val, unit=unit, seq=i))
        # 各类别细分（按类型覆盖）
        db.execute(sa_delete(EvalPerClass).where(EvalPerClass.modelType == model_type))
        for i, pc in enumerate(result["perClass"]):
            db.add(EvalPerClass(modelType=model_type, label=pc["label"],
                                precision=pc["precision"], recall=pc["recall"],
                                f1=pc["f1"], seq=i))
        # 错误案例（按类型覆盖为本次真实错例）
        db.execute(sa_delete(ErrorCase).where(ErrorCase.modelType == model_type))
        for ec in result["errors"]:
            db.add(ErrorCase(errorType=ec["errorType"], content=ec["content"],
                             expected=ec["expected"], actual=ec["actual"],
                             modelType=model_type, count=1))
        # 评估任务收尾
        et = db.get(EvalTask, eid)
        if et:
            et.f1 = result["f1"]
            et.precision = result["precision"]
            et.recall = result["recall"]
            et.status = "已完成"
        # 回写模型版本：F1 + 状态（待评估 → 已评估）
        if model_id.startswith("mv:"):
            mv = db.get(ModelVersion, int(model_id[3:]))
            if mv:
                mv.f1 = result["f1"]
                if mv.status in ("evaluating", None):
                    mv.status = "evaluated"
        db.commit()


runner = EvalRunner()
