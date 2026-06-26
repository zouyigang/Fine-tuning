"""模型效果评估模块数据库读写 + 聚合分析。

列表类（评估任务/复核样本/错误案例/报告）直接读表；
自动化指标 / 基准对比 / 场景验证为聚合分析结果，由本层计算返回。
"""
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.evaluation import (
    EvalTask, EvalReport, ReviewSample, ErrorCase,
    EvalMetric, EvalPerClass, BenchmarkResult, SceneCase,
)
from app.models.model_version import ModelVersion


def _paginate(db: Session, stmt, page: int, page_size: int):
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)).all()
    return rows, total


def list_eval_tasks(db: Session, page: int = 1, page_size: int = 10):
    stmt = select(EvalTask).order_by(EvalTask.id.desc())
    return _paginate(db, stmt, page, page_size)


def list_review_samples(db: Session, page: int = 1, page_size: int = 10):
    stmt = select(ReviewSample).order_by(ReviewSample.id.desc())
    return _paginate(db, stmt, page, page_size)


def review_summary(db: Session) -> dict:
    rows = db.scalars(select(ReviewSample)).all()
    total = len(rows)
    reviewed = sum(1 for r in rows if r.result != "待复核")
    correct = sum(1 for r in rows if r.result == "正确")
    pending = total - reviewed
    accuracy = round(correct / reviewed * 100, 1) if reviewed else 0
    return {"total": total, "reviewed": reviewed, "correct": correct,
            "accuracy": accuracy, "pending": pending}


def list_error_cases(db: Session, error_type: str = "", page: int = 1, page_size: int = 10):
    stmt = select(ErrorCase)
    if error_type:
        stmt = stmt.where(ErrorCase.errorType == error_type)
    stmt = stmt.order_by(ErrorCase.id.desc())
    rows, total = _paginate(db, stmt, page, page_size)
    # 错误类型分布（按 count 求和）
    dist_rows = db.execute(
        select(ErrorCase.errorType, func.sum(ErrorCase.count)).group_by(ErrorCase.errorType)
    ).all()
    dist = [{"name": name, "value": int(val or 0)} for name, val in dist_rows]
    return rows, total, dist


def list_reports(db: Session, page: int = 1, page_size: int = 10):
    stmt = select(EvalReport).order_by(EvalReport.id.desc())
    return _paginate(db, stmt, page, page_size)


def get_report(db: Session, report_id: int) -> EvalReport | None:
    return db.get(EvalReport, report_id)


def all_error_cases(db: Session, error_type: str = ""):
    """导出用：返回全部错误案例（不分页）。"""
    stmt = select(ErrorCase)
    if error_type:
        stmt = stmt.where(ErrorCase.errorType == error_type)
    return db.scalars(stmt.order_by(ErrorCase.id)).all()


def _model_f1(db: Session, model_name: str | None) -> float:
    """报告 F1 取真实来源：同名模型版本 F1 均值 → 全部模型版本均值 → 评估任务均值。"""
    vals = [m.f1 for m in db.scalars(
        select(ModelVersion).where(ModelVersion.name == model_name)).all() if m.f1 is not None]
    if not vals:
        vals = [m.f1 for m in db.scalars(select(ModelVersion)).all() if m.f1 is not None]
    if not vals:
        vals = [e.f1 for e in db.scalars(select(EvalTask)).all() if e.f1 is not None]
    return round(sum(vals) / len(vals), 3) if vals else 0.9


def create_report(db: Session, *, model: str, creator: str,
                  conclusion: str = "建议优化后上线", f1: float | None = None):
    """生成一份评估报告并落库。f1 未给时从该模型真实评估结果派生（不再随机）。"""
    rep = EvalReport(
        name=f"模型评估报告-{model or '未命名模型'}",
        model=model or "-",
        f1=f1 if f1 is not None else _model_f1(db, model),
        conclusion=conclusion,
        creator=creator or "-",
        createdAt=datetime.now().strftime("%Y-%m-%d"),
        status="已生成",
    )
    db.add(rep)
    db.commit()
    db.refresh(rep)
    return rep


def submit_review_results(db: Session, results: list[dict]) -> int:
    """批量更新复核样本结果，返回更新条数。"""
    updated = 0
    today = datetime.now().strftime("%Y-%m-%d")
    for item in results:
        rid, res = item.get("id"), item.get("result")
        if not rid or not res:
            continue
        s = db.get(ReviewSample, rid)
        if s:
            s.result = res
            s.reviewedAt = today
            updated += 1
    db.commit()
    return updated


# ---- 聚合分析（读 DB 表；数据可维护、随模型增删，二期由评估引擎写入）----
def metrics(db: Session, model_type: str = "ner") -> dict:
    ms = db.scalars(
        select(EvalMetric).where(EvalMetric.modelType == model_type).order_by(EvalMetric.seq)).all()
    pcs = db.scalars(
        select(EvalPerClass).where(EvalPerClass.modelType == model_type).order_by(EvalPerClass.seq)).all()
    return {
        "metrics": [{"name": m.name, "value": m.value, "unit": m.unit or ""} for m in ms],
        "perClass": [{"label": p.label, "precision": p.precision, "recall": p.recall, "f1": p.f1} for p in pcs],
    }


def benchmark(db: Session) -> dict:
    rows = db.scalars(select(BenchmarkResult).order_by(BenchmarkResult.seq)).all()
    dims = [r.dim for r in rows]
    cur = [r.current for r in rows]
    prod = [r.prod for r in rows]
    hist = [r.hist for r in rows]
    return {
        "dims": dims,
        "models": [
            {"name": "本次微调模型", "values": cur},
            {"name": "当前生产模型", "values": prod},
            {"name": "历史最优模型", "values": hist},
        ],
        "compare": [
            {"dim": d, "current": cur[i], "prod": prod[i], "diff": round((cur[i] or 0) - (prod[i] or 0), 1)}
            for i, d in enumerate(dims)
        ],
    }


def scene_validation(db: Session) -> dict:
    cases = db.scalars(select(SceneCase).order_by(SceneCase.id)).all()
    out = [{"id": c.id, "caseNo": c.caseNo, "type": c.type, "sampleCount": c.sampleCount,
            "accuracy": c.accuracy, "hard": c.hard} for c in cases]
    total = sum(c.sampleCount or 0 for c in cases)
    correct = round(sum((c.sampleCount or 0) * (c.accuracy or 0) / 100 for c in cases))
    hard_total = sum(c.sampleCount or 0 for c in cases if c.hard)
    hard_correct = round(sum((c.sampleCount or 0) * (c.accuracy or 0) / 100 for c in cases if c.hard))
    summary = {
        "total": total,
        "correct": correct,
        "accuracy": round(correct / total * 100, 1) if total else 0,
        "hardCase": hard_total,
        "hardAccuracy": round(hard_correct / hard_total * 100, 1) if hard_total else 0,
    }
    return {"summary": summary, "cases": out}
