"""真实微调引擎（M1）：调 LLaMA-Factory 跑训练，回流真实指标/日志，完成自动建 model_version。

设计要点（详见 docs/真实微调引擎方案.md）：
- 每个任务起独立 subprocess(`llamafactory-cli train <yaml>`)，崩溃不拖垮 API，可 kill；
- 监控线程增量读 LF 的 output_dir/trainer_log.jsonl → 写 train_metric，进程 stdout/err → 写 train_log；
- 进程退出码 0 → status=success + 建 model_version + 写 task_artifact；非 0 → failed + error_msg；
- 并发闸 MAX_CONCURRENT_TRAINS（一般=GPU 数），超额任务留 pending 排队。
- 仅 ENGINE_MODE=real 生效；sim 模式由 trainer.py 的模拟调度器负责。
"""
import json
import os
import subprocess
import sys
import threading
import time
from datetime import datetime

from sqlalchemy import select, func

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.task import TrainTask, TrainMetric, TrainLog, TaskArtifact
from app.models.model_version import ModelVersion
from app.services import engine_config as ec


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _log(db, task_id: int, level: str, msg: str):
    db.add(TrainLog(task_id=task_id, time=_now(), level=level, msg=msg[:500]))
    db.commit()


class TrainingManager:
    """单例：管理训练任务的排队、启动、监控、收尾。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._running: dict[int, subprocess.Popen] = {}  # task_id -> Popen
        self._device: dict[int, int] = {}                # task_id -> GPU 序号
        self._intent: dict[int, str] = {}                # task_id -> 用户主动目标态(paused/stopped)
        self._oom: set[int] = set()                      # 检测到 OOM 的 task_id
        self._gpu_count: int | None = None
        self._started = False

    # ---- GPU 探测 / 设备分配 ----
    def gpu_count(self) -> int:
        """探测可用 GPU 数：优先 pynvml，回退 torch，再回退 1。结果缓存。"""
        if self._gpu_count is not None:
            return self._gpu_count
        n = 0
        try:
            import pynvml
            pynvml.nvmlInit()
            n = pynvml.nvmlDeviceGetCount()
            pynvml.nvmlShutdown()
        except Exception:
            try:
                import torch
                n = torch.cuda.device_count()
            except Exception:
                n = 0
        self._gpu_count = max(1, n)
        return self._gpu_count

    def concurrency(self) -> int:
        """有效并发 = min(配置上限, GPU 数)。"""
        return max(1, min(settings.MAX_CONCURRENT_TRAINS, self.gpu_count()))

    def _pick_device(self) -> int:
        """选一张未被占用的 GPU 序号（持锁调用）。"""
        used = set(self._device.values())
        for i in range(self.gpu_count()):
            if i not in used:
                return i
        return 0

    def _sample_gpu(self, device: int | None) -> int:
        """采样指定 GPU 的利用率（pynvml）；不可用返回 0。"""
        if device is None:
            return 0
        try:
            import pynvml
            pynvml.nvmlInit()
            h = pynvml.nvmlDeviceGetHandleByIndex(device)
            util = pynvml.nvmlDeviceGetUtilizationRates(h).gpu
            pynvml.nvmlShutdown()
            return int(util)
        except Exception:
            return 0

    def gpu_status(self) -> list[dict]:
        """各 GPU 实时状态（pynvml）：序号/名称/显存/利用率/当前训练任务。供监控页展示。"""
        out = []
        dev2task = {v: k for k, v in self._device.items()}
        try:
            import pynvml
            pynvml.nvmlInit()
            for i in range(pynvml.nvmlDeviceGetCount()):
                h = pynvml.nvmlDeviceGetHandleByIndex(i)
                mem = pynvml.nvmlDeviceGetMemoryInfo(h)
                util = pynvml.nvmlDeviceGetUtilizationRates(h)
                name = pynvml.nvmlDeviceGetName(h)
                out.append({
                    "index": i,
                    "name": name.decode() if isinstance(name, bytes) else name,
                    "memUsedMB": round(mem.used / 1024 / 1024),
                    "memTotalMB": round(mem.total / 1024 / 1024),
                    "util": util.gpu,
                    "taskId": dev2task.get(i),
                })
            pynvml.nvmlShutdown()
        except Exception as e:
            return [{"error": f"GPU 信息不可用: {e}"}]
        return out

    # ---- 对外控制 ----
    def start(self):
        """随应用启动：拉起一个调度线程，周期把 pending 任务投入空闲 GPU。"""
        if self._started:
            return
        self._started = True
        threading.Thread(target=self._scheduler_loop, daemon=True).start()
        print(f"真实微调引擎已启动（ENGINE_MODE=real, GPU={self.gpu_count()}, 并发={self.concurrency()}）", flush=True)

    def stop_task(self, task_id: int, target_status: str = "stopped") -> bool:
        """终止训练子进程。target_status 记为用户主动目标态，避免被收尾误判为 failed。"""
        with self._lock:
            p = self._running.get(task_id)
            if p:
                self._intent[task_id] = target_status
        if not p:
            return False
        try:
            p.terminate()
            return True
        except Exception:
            return False

    # ---- 调度 ----
    def _scheduler_loop(self):
        while True:
            try:
                self._dispatch_once()
            except Exception as e:  # 调度器自身不能崩
                print(f"[engine] 调度异常: {e}", flush=True)
            time.sleep(5)

    def _dispatch_once(self):
        with self._lock:
            free = self.concurrency() - len(self._running)
        if free <= 0:
            return
        db = SessionLocal()
        try:
            pending = db.scalars(
                select(TrainTask).where(TrainTask.status == "pending").order_by(TrainTask.id)
            ).all()
        finally:
            db.close()
        for t in pending[:free]:
            self._launch(t.id)

    def _launch(self, task_id: int):
        """准备配置并起子进程；准备失败直接置 failed。"""
        with self._lock:
            if task_id in self._running:
                return
        db = SessionLocal()
        try:
            t = db.get(TrainTask, task_id)
            if not t or t.status != "pending":
                return
            try:
                model_path = ec.resolve_model_path(t.baseModel)
                if not model_path:
                    raise ValueError(f"未在 MODELS_DIR 找到基础模型「{t.baseModel}」的离线权重")
                dataset_key = self._prepare_dataset(db, t)
                template = ec.template_for(t.baseModel)
                # 断点续训：输出目录已有 checkpoint（多为重试场景）则从断点恢复
                prev_out = os.path.join(settings.RUNS_DIR, str(t.id), "output")
                resume = ec.has_checkpoint(os.path.abspath(prev_out))
                yaml_path, output_dir = ec.build_train_yaml(
                    task_id=t.id, model_path=model_path, dataset_key=dataset_key,
                    template=template, method=(t.method or "lora"), hp=t.hyperparams or {},
                    resume=resume,
                )
                if resume:
                    _log(db, t.id, "INFO", "检测到已有 checkpoint，将从断点续训")
            except Exception as e:
                t.status = "failed"
                t.errorMsg = str(e)[:500]
                t.finishedAt = _now()
                db.commit()
                _log(db, t.id, "ERROR", f"准备训练失败: {e}")
                return

            t.status = "running"
            t.progress = 0
            t.baseModelPath = model_path
            t.outputDir = output_dir
            db.commit()
            _log(db, t.id, "INFO", f"开始训练: model={os.path.basename(model_path)} "
                                   f"method={t.method} dataset={dataset_key} template={template}")
        finally:
            db.close()

        with self._lock:
            device = self._pick_device()
        cmd = self._build_cmd("train", yaml_path)
        env = dict(os.environ)
        env["CUDA_VISIBLE_DEVICES"] = str(device)
        env["PYTHONUTF8"] = "1"
        try:
            proc = subprocess.Popen(
                cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="ignore", bufsize=1,
            )
        except Exception as e:
            self._finish(task_id, ok=False, error=f"启动子进程失败: {e}")
            return
        with self._lock:
            self._running[task_id] = proc
            self._device[task_id] = device
        db = SessionLocal()
        try:
            t = db.get(TrainTask, task_id)
            if t:
                t.pid = proc.pid
                db.commit()
        finally:
            db.close()
        # 每个任务两条线程：读 stdout 写日志 / 轮询 trainer_log.jsonl 写指标
        threading.Thread(target=self._pump_stdout, args=(task_id, proc), daemon=True).start()
        threading.Thread(target=self._watch, args=(task_id, proc), daemon=True).start()

    def _build_cmd(self, verb: str, yaml_path: str) -> list[str]:
        if settings.LLAMAFACTORY_BIN:
            return [settings.LLAMAFACTORY_BIN, verb, yaml_path]
        return [sys.executable, "-m", "llamafactory.cli", verb, yaml_path]

    def _prepare_dataset(self, db, t: TrainTask) -> str:
        """把任务关联的上传文件注册为 LF 数据集，返回数据集名。

        M1：用任务 dataset 字段匹配最近一次该数据集的上传文件。匹配不到时
        回退 LF 内置 demo 数据集 alpaca_zh_demo，保证链路可跑通。
        """
        from app.models.dataset import DatasetFile, Dataset
        from app.core import storage as st

        # 优先：dataset 字段是数据集 id 或名称 → 找其上传文件
        rec = None
        ds_name = t.dataset or ""
        ds = None
        if ds_name.isdigit():
            ds = db.get(Dataset, int(ds_name))
        if ds is None and ds_name:
            ds = db.scalars(select(Dataset).where(Dataset.name == ds_name)).first()
        if ds is not None:
            rec = db.scalars(
                select(DatasetFile).where(DatasetFile.dataset_id == ds.id)
                .order_by(DatasetFile.id.desc())
            ).first()
        if rec is not None:
            abspath = st.abspath_of("datasets", rec.storedName)
            return ec.register_dataset(f"ds{ds.id}", abspath, ds_type=ds.type)
        _log(db, t.id, "WARN", f"未找到数据集「{ds_name}」的上传文件，回退内置 demo 数据集")
        return ec.ensure_demo_dataset()

    # ---- 监控 ----
    def _pump_stdout(self, task_id: int, proc: subprocess.Popen):
        db = SessionLocal()
        try:
            for line in proc.stdout:
                line = (line or "").rstrip()
                if not line:
                    continue
                low = line.lower()
                if "out of memory" in low or "cuda out of memory" in low or "outofmemoryerror" in low:
                    self._oom.add(task_id)
                level = "ERROR" if ("Error" in line or "Traceback" in line) else \
                        ("WARN" if "warn" in low else "INFO")
                _log(db, task_id, level, line)
        except Exception:
            pass
        finally:
            db.close()

    def _watch(self, task_id: int, proc: subprocess.Popen):
        """轮询 trainer_log.jsonl 增量行 → 写 train_metric；进程结束后收尾。"""
        db = SessionLocal()
        log_path = None
        seen = 0
        try:
            t = db.get(TrainTask, task_id)
            log_path = os.path.join(t.outputDir, "trainer_log.jsonl") if t and t.outputDir else None
            while proc.poll() is None:
                seen = self._drain_metrics(db, task_id, log_path, seen)
                time.sleep(3)
            # 进程已退出：再收一次尾部指标
            seen = self._drain_metrics(db, task_id, log_path, seen)
        except Exception as e:
            try:
                db.rollback()
                _log(db, task_id, "ERROR", f"监控异常: {e}")
            except Exception:
                pass
        finally:
            db.close()
        # 无论监控是否异常，都必须回收子进程并收尾，否则任务永卡 running + 僵尸进程
        try:
            proc.wait(timeout=10)
        except Exception:
            pass
        code = proc.returncode
        with self._lock:
            self._running.pop(task_id, None)
            self._device.pop(task_id, None)
            intent = self._intent.pop(task_id, None)
        if intent:
            # 用户主动暂停/终止：按目标态落库，不算失败、不建模型版本
            self._mark(task_id, intent)
        else:
            self._finish(task_id, ok=(code == 0), error=None if code == 0 else f"训练进程退出码 {code}")

    def _drain_metrics(self, db, task_id: int, log_path: str | None, seen: int) -> int:
        if not log_path or not os.path.exists(log_path):
            return seen
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except Exception:
            return seen
        if len(lines) <= seen:
            return seen
        t = db.get(TrainTask, task_id)
        gpu_util = self._sample_gpu(self._device.get(task_id))
        for line in lines[seen:]:
            s = line.strip()
            if not s:
                continue
            try:
                rec = json.loads(s)
            except Exception:
                continue
            step = rec.get("current_steps") or rec.get("step") or 0
            loss = rec.get("loss")
            val = rec.get("eval_loss")
            pct = rec.get("percentage")
            if loss is None and val is None:
                continue
            db.add(TrainMetric(task_id=task_id, step=step, loss=loss, valLoss=val, acc=None, gpu=gpu_util))
            if t:
                if loss is not None:
                    t.loss = str(round(float(loss), 4))
                if pct is not None:
                    t.progress = min(99, int(pct))
                ep = rec.get("epoch")
                if ep is not None:
                    # epoch 列仅 VARCHAR(16)，LF 给的浮点 epoch（如 7.666666666666667）
                    # 原样写入会触发 DataError(1406) Data too long，进而拖垮整个监控线程，
                    # 导致任务永卡 running + 子进程僵尸不回收。故统一压成 2 位小数。
                    try:
                        t.epoch = f"{float(ep):.2f}"
                    except (TypeError, ValueError):
                        t.epoch = str(ep)[:16]
        try:
            db.commit()
        except Exception:
            # 单批指标写失败不致命：回滚保持会话可用，下个轮询周期重试
            db.rollback()
            return seen
        return len(lines)

    # ---- 收尾 ----
    def _mark(self, task_id: int, status: str):
        """用户主动暂停/终止后的落库（不建模型版本）。"""
        db = SessionLocal()
        try:
            t = db.get(TrainTask, task_id)
            if not t:
                return
            t.status = status
            t.pid = None
            t.finishedAt = _now()
            db.commit()
            _log(db, task_id, "WARN", "已暂停（进程已停止）" if status == "paused" else "已终止")
        finally:
            db.close()

    def _finish(self, task_id: int, *, ok: bool, error: str | None):
        db = SessionLocal()
        try:
            t = db.get(TrainTask, task_id)
            if not t:
                return
            t.finishedAt = _now()
            t.pid = None
            if ok:
                t.status = "success"
                t.progress = 100
                _log(db, task_id, "INFO", "训练完成，最佳权重已保存")
                self._make_model_version(db, t)
            else:
                t.status = "failed"
                if task_id in self._oom:
                    t.errorMsg = "显存不足（CUDA OOM）：建议改用 QLoRA、减小批次大小、缩短最大序列长度或更换更小模型"
                else:
                    t.errorMsg = (error or "训练失败")[:500]
                _log(db, task_id, "ERROR", t.errorMsg)
            self._oom.discard(task_id)
            db.commit()
        finally:
            db.close()

    def _make_model_version(self, db, t: TrainTask):
        """训练成功 → 建 model_version（待评估）+ 写产物（adapter；LoRA 再合并出 merged）。"""
        from app.core import storage as st

        ver = self._next_version(db, t.name)
        mv = ModelVersion(
            name=t.name, version=ver, modelType=t.modelType, dataset=t.dataset,
            f1=None, size="-", status="evaluating", trainAt=_now(),
            creator=t.creator, task_id=t.id,
        )
        db.add(mv)
        db.commit()
        db.refresh(mv)
        t.modelVersionId = mv.id

        if t.outputDir and os.path.isdir(t.outputDir):
            out_size = self._dir_size(t.outputDir)
            if t.method == "full":
                # 全参微调：输出目录即完整权重
                mv.size = st.human_size(out_size)
                db.add(TaskArtifact(task_id=t.id, kind="merged", path=t.outputDir,
                                    size=st.human_size(out_size), createdAt=_now()))
            else:
                # LoRA/QLoRA：先记 adapter 产物
                db.add(TaskArtifact(task_id=t.id, kind="adapter", path=t.outputDir,
                                    size=st.human_size(out_size), createdAt=_now()))
                mv.size = st.human_size(out_size)
        db.commit()
        _log(db, t.id, "INFO", f"已生成模型版本 {t.name} {ver}（待评估）")

        # LoRA/QLoRA：合并 adapter 进基座，导出完整权重（best-effort，失败不影响版本）
        if t.method in (None, "lora", "qlora") and t.baseModelPath and t.outputDir \
                and os.path.exists(os.path.join(t.outputDir, "adapter_config.json")):
            self._merge_export(db, t, mv)

    def _merge_export(self, db, t: TrainTask, mv: ModelVersion):
        from app.core import storage as st
        export_dir = os.path.abspath(os.path.join(settings.RUNS_DIR, str(t.id), "merged"))
        template = ec.template_for(t.baseModel)
        try:
            yaml_path = ec.build_export_yaml(
                task_id=t.id, model_path=t.baseModelPath, adapter_dir=t.outputDir,
                template=template, export_dir=export_dir,
            )
        except Exception as e:
            _log(db, t.id, "WARN", f"生成合并配置失败，跳过 merge: {e}")
            return
        _log(db, t.id, "INFO", "开始合并 LoRA 权重导出完整模型...")
        cmd = self._build_cmd("export", yaml_path)
        env = dict(os.environ)
        env["CUDA_VISIBLE_DEVICES"] = str(self._device.get(t.id, 0))
        env["PYTHONUTF8"] = "1"
        try:
            proc = subprocess.run(cmd, env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT, text=True,
                                  encoding="utf-8", errors="ignore", timeout=1800)
        except Exception as e:
            _log(db, t.id, "WARN", f"合并导出启动失败: {e}")
            return
        if proc.returncode == 0 and os.path.isdir(export_dir):
            size = self._dir_size(export_dir)
            db.add(TaskArtifact(task_id=t.id, kind="merged", path=export_dir,
                                size=st.human_size(size), createdAt=_now()))
            mv.size = st.human_size(size)
            db.commit()
            _log(db, t.id, "INFO", f"已合并导出完整模型至 {export_dir}（{st.human_size(size)}）")
        else:
            _log(db, t.id, "WARN", f"合并导出失败（退出码 {proc.returncode}），仅保留 adapter 产物")

    def _next_version(self, db, name: str) -> str:
        cnt = db.scalar(select(func.count(ModelVersion.id)).where(ModelVersion.name == name)) or 0
        return f"v1.{cnt}"

    def _dir_size(self, path: str) -> int:
        total = 0
        for root, _, files in os.walk(path):
            for fn in files:
                try:
                    total += os.path.getsize(os.path.join(root, fn))
                except OSError:
                    pass
        return total


manager = TrainingManager()


def start_engine():
    """供 main lifespan 调用：real 模式启动真实引擎调度。"""
    manager.start()
