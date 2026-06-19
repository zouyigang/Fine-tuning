"""微调任务模块数据库读写。"""
import random

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.task import TrainTask, TrainMetric, TrainLog

TOTAL_STEPS = 20000


def list_tasks(db: Session, keyword: str = "", status: str = "", page: int = 1, page_size: int = 10):
    stmt = select(TrainTask)
    if keyword:
        stmt = stmt.where(TrainTask.name.like(f"%{keyword}%"))
    if status:
        stmt = stmt.where(TrainTask.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(TrainTask.id.desc()).offset((page - 1) * page_size).limit(page_size)
    return db.scalars(stmt).all(), total


def create_task(db: Session, payload: dict) -> TrainTask:
    # 新建即进入训练（status=running），由调度器推进进度
    item = TrainTask(status="running", progress=0, loss="-", **payload)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_status(db: Session, task_id: int, status: str) -> bool:
    t = db.get(TrainTask, task_id)
    if not t:
        return False
    t.status = status
    db.commit()
    return True


def metric_count(db: Session, task_id: int) -> int:
    return db.scalar(select(func.count(TrainMetric.id)).where(TrainMetric.task_id == task_id)) or 0


def get_metrics(db: Session, task_id: int):
    return db.scalars(
        select(TrainMetric).where(TrainMetric.task_id == task_id).order_by(TrainMetric.step)
    ).all()


def current_running(db: Session) -> TrainTask | None:
    """当前监控目标：指标点最多的运行中任务（稳定指向常驻演示任务）。"""
    running = db.scalars(select(TrainTask).where(TrainTask.status == "running")).all()
    if not running:
        return None
    running.sort(key=lambda t: (metric_count(db, t.id), t.id), reverse=True)
    return running[0]


def running_payload(db: Session, t: TrainTask) -> dict:
    metrics = get_metrics(db, t.id)
    last = metrics[-1] if metrics else None
    step = last.step if last else 0
    shown_step = min(step, TOTAL_STEPS)
    remaining = max(0, TOTAL_STEPS - step)
    return {
        "id": t.id,
        "name": t.name,
        "status": "running",
        "progress": t.progress or 0,
        "epoch": t.epoch or "1/10",
        "step": f"{shown_step}/{TOTAL_STEPS}",
        "eta": f"约 {max(1, remaining // 500)} 分钟",
        "gpuUtil": last.gpu if last else random.randint(80, 95),
        "gpuMem": round((last.gpu if last else 85) / 100 * 40, 1),
        "cpuUtil": random.randint(20, 45),
        "curLoss": last.loss if last else None,
        "curAcc": last.acc if last else None,
    }


def training_curve(db: Session, t: TrainTask) -> dict:
    metrics = get_metrics(db, t.id)[-40:]  # 仅取最近 40 个点，避免曲线无限增长
    return {
        "steps": [m.step for m in metrics],
        "loss": [m.loss for m in metrics],
        "valLoss": [m.valLoss for m in metrics],
        "acc": [m.acc for m in metrics],
        "gpu": [m.gpu for m in metrics],
    }


def resource_usage(db: Session, t: TrainTask) -> dict:
    metrics = get_metrics(db, t.id)[-30:]
    return {
        "points": [f"{i}s" for i in range(len(metrics))],
        "gpu": [m.gpu for m in metrics],
        "cpu": [round(m.gpu * 0.45) for m in metrics],   # 与 GPU 相关，稳定不抖动
        "mem": [round(m.gpu * 0.8) for m in metrics],
    }


def get_logs(db: Session, task_id: int, level: str = "", keyword: str = "", limit: int = 300):
    stmt = select(TrainLog).where(TrainLog.task_id == task_id)
    if level:
        stmt = stmt.where(TrainLog.level == level)
    if keyword:
        stmt = stmt.where(TrainLog.msg.like(f"%{keyword}%"))
    stmt = stmt.order_by(TrainLog.id).limit(limit)
    return db.scalars(stmt).all()


def schedule_queue(db: Session):
    return db.scalars(
        select(TrainTask)
        .where(TrainTask.status.in_(["pending", "running"]))
        .order_by(TrainTask.id)
        .limit(8)
    ).all()
