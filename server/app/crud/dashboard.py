"""工作台总览聚合：从各业务表实时汇总首页所需数据。"""
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.crud import screen as screen_crud
from app.models.dataset import Dataset
from app.models.task import TrainTask
from app.models.model_version import ModelVersion
from app.models.evaluation import EvalReport, ReviewSample


def _count(db: Session, model, *conds) -> int:
    stmt = select(func.count()).select_from(model)
    for c in conds:
        stmt = stmt.where(c)
    return db.scalar(stmt) or 0


def _parse_dt(s):
    """容错解析 '2026-06-05 03:30' 之类字符串为 datetime（按日粒度）；失败返回 None。"""
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d")
    except ValueError:
        return None


def _wow_growth(rows, attr, is_datetime=False, days=7):
    """周环比增长率（%）：近 days 天新增 vs 前 days 天新增。

    指标卡的 trend 指示。上一周期为 0 时：本期有增量记 100%，否则 None
    （前端 StatCard 对 trend===null 自动隐藏箭头，避免造数）。
    """
    now = datetime.now()
    recent_start = now - timedelta(days=days)
    prev_start = now - timedelta(days=days * 2)
    recent = prev = 0
    for r in rows:
        v = getattr(r, attr, None)
        dt = v if is_datetime else _parse_dt(v)
        if not dt:
            continue
        if dt >= recent_start:
            recent += 1
        elif dt >= prev_start:
            prev += 1
    if prev == 0:
        return 100 if recent else None
    return round((recent - prev) / prev * 100)


def _recent_tasks(db: Session, limit: int = 5) -> list:
    """最近微调任务（取最新 limit 条），供总览首屏与 5s 轮询共用。"""
    recent = db.scalars(select(TrainTask).order_by(TrainTask.id.desc()).limit(limit)).all()
    return [
        {"name": t.name, "status": t.status, "progress": t.progress or 0, "creator": t.creator}
        for t in recent
    ]


def live(db: Session) -> dict:
    """工作台 5s 轮询的「会动」字段：GPU 实时 + 进行中任务数 + 最近任务进度。

    趋势图/饼图/数据集总数等慢变或重绘代价大的部分不在此返回，由首屏快照保持。
    """
    running = _count(db, TrainTask, TrainTask.status == "running")
    return {
        "gpu": screen_crud.gpu_realtime(db),
        "runningCount": running,
        "recentTasks": _recent_tasks(db),
    }


def overview(db: Session) -> dict:
    datasets = db.scalars(select(Dataset)).all()
    tasks_all = db.scalars(select(TrainTask)).all()
    models_all = db.scalars(select(ModelVersion)).all()

    ds_total = len(datasets)
    running = sum(1 for t in tasks_all if t.status == "running")
    online = sum(1 for m in models_all if m.status == "online")

    # GPU 使用率：real 模式取真实 pynvml；否则回退 cluster_info（与大屏共用同一来源）
    gpu = screen_crud.gpu_realtime(db)

    stats = [
        {"label": "数据集总数", "value": ds_total, "unit": "个", "icon": "Coin", "bg": "#2f54eb",
         "trend": _wow_growth(datasets, "created_at", is_datetime=True)},
        {"label": "进行中微调任务", "value": running, "unit": "个", "icon": "SetUp", "bg": "#13c2c2",
         "trend": _wow_growth(tasks_all, "createdAt")},
        {"label": "已上线模型", "value": online, "unit": "个", "icon": "Box", "bg": "#52c41a",
         "trend": _wow_growth(models_all, "trainAt")},
        # GPU 使用率为实时瞬时值，无历史时序，不造环比；trend=None 前端隐藏箭头。
        # sub 显示真实显存占用（更直观），前端每 5s 轮询刷新本卡。
        {"label": "GPU 资源使用率", "value": gpu["util"], "unit": "%", "icon": "Cpu", "bg": "#fa8c16",
         "trend": None, "sub": gpu["sub"]},
    ]

    # 近 14 天任务趋势（真实：按 TrainTask 的 createdAt / finishedAt 日期聚合）
    task_trend = screen_crud.task_trend(db)

    # 模型类型分布（真实聚合）
    dist_rows = db.execute(
        select(ModelVersion.modelType, func.count())
        .group_by(ModelVersion.modelType)
        .order_by(func.count().desc())
    ).all()
    model_type_dist = [{"name": name or "未分类", "value": cnt} for name, cnt in dist_rows]

    # 最近微调任务（真实，取最新 5 条；与 live() 共用同一构造）
    recent_tasks = _recent_tasks(db)

    # 待办事项（真实聚合：待审批报告 / 待复核样本 / 失败任务 / 待评估模型）
    pending_reports = _count(db, EvalReport, EvalReport.status == "待审批")
    pending_reviews = _count(db, ReviewSample, ReviewSample.result == "待复核")
    failed_tasks = _count(db, TrainTask, TrainTask.status == "failed")
    evaluating = _count(db, ModelVersion, ModelVersion.status == "evaluating")
    todos = []
    if pending_reports:
        todos.append({"type": "待审批", "text": f"{pending_reports} 份评估报告待审批", "level": "danger"})
    if evaluating:
        todos.append({"type": "待评估", "text": f"{evaluating} 个模型处于评估中，待生成报告", "level": "warning"})
    if pending_reviews:
        todos.append({"type": "待复核", "text": f"{pending_reviews} 条人工复核样本待处理", "level": "warning"})
    if failed_tasks:
        todos.append({"type": "告警", "text": f"{failed_tasks} 个微调任务训练失败，需排查", "level": "danger"})

    return {
        "stats": stats,
        "taskTrend": task_trend,
        "modelTypeDist": model_type_dist,
        "recentTasks": recent_tasks,
        "todos": todos,
    }
