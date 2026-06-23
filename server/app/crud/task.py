"""微调任务模块数据库读写。"""
import random
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.task import TrainTask, TrainMetric, TrainLog, ScheduleItem

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
    # real：入队等待真实引擎调度（pending）；sim：创建即 running，由模拟调度器推进
    from app.core.config import settings
    init_status = "pending" if settings.ENGINE_MODE == "real" else "running"
    item = TrainTask(status=init_status, progress=0, loss="-", **payload)
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


def apply_hyperparams(db: Session, task_id: int, hyperparams: dict, method: str | None = None):
    """把超参（可含微调方式）应用到任务。运行中/已完成任务不允许改。返回 (ok, msg)。"""
    t = db.get(TrainTask, task_id)
    if not t:
        return False, "任务不存在"
    if t.status in ("running", "success"):
        return False, "运行中或已完成的任务不可修改超参"
    t.hyperparams = hyperparams
    if method:
        t.method = method
    db.commit()
    return True, "已应用"


def requeue_task(db: Session, task_id: int) -> bool:
    """继续/重试：重置运行态字段并置 pending，交由真实引擎调度器重新拉起。"""
    t = db.get(TrainTask, task_id)
    if not t:
        return False
    t.status = "pending"
    t.progress = 0
    t.pid = None
    t.errorMsg = None
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


def _ensure_schedule_seed(db: Session):
    """调度队列为空时，以当前排队/运行任务初始化（首次访问自动播种）。"""
    if db.scalar(select(func.count(ScheduleItem.id))):
        return
    tasks = db.scalars(
        select(TrainTask)
        .where(TrainTask.status.in_(["pending", "running"]))
        .order_by(TrainTask.id)
        .limit(8)
    ).all()
    for i, t in enumerate(tasks):
        db.add(ScheduleItem(
            task_id=t.id, name=t.name, priority=t.priority or "中", status=t.status,
            gpu=t.gpu or "-", seq=i + 1,
            scheduledAt="立即执行" if i < 2 else f"2026-06-09 0{i}:00",
        ))
    db.commit()


def schedule_queue(db: Session):
    """返回持久化的调度队列（按 seq 升序）。"""
    _ensure_schedule_seed(db)
    items = db.scalars(select(ScheduleItem).order_by(ScheduleItem.seq, ScheduleItem.id)).all()
    out = []
    for i, s in enumerate(items):
        out.append({
            "id": s.id, "taskId": s.task_id, "name": s.name,
            "priority": s.priority, "status": s.status, "gpu": s.gpu,
            "scheduledAt": s.scheduledAt, "order": i + 1,
        })
    return out


def create_schedule_item(db: Session, payload: dict) -> ScheduleItem:
    """新建批量调度项，追加到队尾。"""
    max_seq = db.scalar(select(func.max(ScheduleItem.seq))) or 0
    item = ScheduleItem(
        task_id=payload.get("taskId"),
        name=payload.get("name") or "未命名批量任务",
        priority=payload.get("priority") or "中",
        status="pending",
        gpu=payload.get("gpu") or "待分配",
        seq=max_seq + 1,
        scheduledAt=payload.get("scheduledAt") or "立即执行",
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def remove_schedule_item(db: Session, item_id: int) -> bool:
    s = db.get(ScheduleItem, item_id)
    if not s:
        return False
    db.delete(s)
    db.commit()
    return True


def reorder_schedule(db: Session, ids: list[int]) -> int:
    """按给定 id 顺序重排 seq。返回更新条数。"""
    updated = 0
    for i, sid in enumerate(ids):
        s = db.get(ScheduleItem, sid)
        if s:
            s.seq = i + 1
            updated += 1
    db.commit()
    return updated
