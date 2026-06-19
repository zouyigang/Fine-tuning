"""工作台总览聚合：从各业务表实时汇总首页所需数据。"""
import random
from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.dataset import Dataset
from app.models.task import TrainTask
from app.models.model_version import ModelVersion
from app.models.evaluation import EvalReport, ReviewSample
from app.models.config import ClusterInfo

# 趋势图锚定日期，保持与前端原 mock 一致、刷新稳定
_TREND_END = datetime(2026, 6, 9)


def _count(db: Session, model, *conds) -> int:
    stmt = select(func.count()).select_from(model)
    for c in conds:
        stmt = stmt.where(c)
    return db.scalar(stmt) or 0


def overview(db: Session) -> dict:
    ds_total = _count(db, Dataset)
    running = _count(db, TrainTask, TrainTask.status == "running")
    online = _count(db, ModelVersion, ModelVersion.status == "online")

    cluster = db.scalars(select(ClusterInfo).limit(1)).first()
    gpu_pct = round(cluster.usedGpu / cluster.totalGpu * 100) if cluster and cluster.totalGpu else 0

    stats = [
        {"label": "数据集总数", "value": ds_total, "unit": "个", "icon": "Coin", "bg": "#2f54eb", "trend": 12},
        {"label": "进行中微调任务", "value": running, "unit": "个", "icon": "SetUp", "bg": "#13c2c2", "trend": 8},
        {"label": "已上线模型", "value": online, "unit": "个", "icon": "Box", "bg": "#52c41a", "trend": 5},
        {"label": "GPU 资源使用率", "value": gpu_pct, "unit": "%", "icon": "Cpu", "bg": "#fa8c16", "trend": -3},
    ]

    # 近 14 天任务趋势（演示数据，锚定固定日期保证稳定）
    dates, created, finished = [], [], []
    for i in range(13, -1, -1):
        d = _TREND_END - timedelta(days=i)
        dates.append(f"{d.month}/{d.day}")
        created.append(random.randint(1, 8))
        finished.append(random.randint(1, 6))
    task_trend = {"dates": dates, "created": created, "finished": finished}

    # 模型类型分布（真实聚合）
    dist_rows = db.execute(
        select(ModelVersion.modelType, func.count())
        .group_by(ModelVersion.modelType)
        .order_by(func.count().desc())
    ).all()
    model_type_dist = [{"name": name or "未分类", "value": cnt} for name, cnt in dist_rows]

    # 最近微调任务（真实，取最新 5 条）
    recent = db.scalars(select(TrainTask).order_by(TrainTask.id.desc()).limit(5)).all()
    recent_tasks = [
        {"name": t.name, "status": t.status, "progress": t.progress or 0, "creator": t.creator}
        for t in recent
    ]

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
