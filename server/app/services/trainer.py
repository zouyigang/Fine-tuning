"""模拟训练调度器（P4）。

用 APScheduler 周期推进所有 status=running 的任务：
- 每 3 秒前进 1000 step，写一条 train_metric（loss/valLoss/acc/gpu）与 train_log；
- 普通任务进度达 100% 自动置为 success；
- 演示任务（id=1）为常驻任务：持续训练、进度封顶 99%、永不结束，
  保证「实时监控」页随时有持续滚动的曲线；若当前无任何运行任务则自动重新拉起它。

不接真实 GPU，纯模拟，足以打通"创建任务 → 实时监控 → 日志"全链路。
"""
import math
import random
from datetime import datetime

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import select, func

from app.core.database import SessionLocal
from app.models.task import TrainTask, TrainMetric, TrainLog

TOTAL_STEPS = 20000
STEP_PER_TICK = 1000
TICK_SECONDS = 3
DEMO_TASK_ID = 1
BACKFILL_POINTS = 13  # 演示任务回填点数（首屏即有曲线）


# ---- 指标公式（按第 i 个点计算，曲线平滑收敛）----
def _loss(i: int) -> float:
    return round(0.85 * math.exp(-i / 6) + 0.06 + random.uniform(0, 0.02), 3)


def _val_loss(i: int) -> float:
    return round(0.9 * math.exp(-i / 6) + 0.08 + random.uniform(0, 0.03), 3)


def _acc(i: int) -> float:
    return round(60 + 36 * (1 - math.exp(-i / 5)) + random.uniform(0, 1), 2)


def _epoch(step: int) -> str:
    return f"{max(1, min(10, step * 10 // TOTAL_STEPS))}/10"


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _metric_count(db, task_id: int) -> int:
    return db.scalar(select(func.count(TrainMetric.id)).where(TrainMetric.task_id == task_id)) or 0


def _advance(db, t: TrainTask):
    """推进单个任务一格。"""
    cnt = _metric_count(db, t.id)
    step = (cnt + 1) * STEP_PER_TICK
    loss, acc, gpu = _loss(cnt), _acc(cnt), random.randint(75, 96)
    db.add(TrainMetric(task_id=t.id, step=step, loss=loss, valLoss=_val_loss(cnt), acc=acc, gpu=gpu))
    db.add(TrainLog(task_id=t.id, time=_now(), level="INFO", msg=f"step {step} | loss={loss} | acc={acc}%"))
    if random.random() < 0.12:
        db.add(TrainLog(task_id=t.id, time=_now(), level="WARN",
                        msg=f"gradient norm {round(random.uniform(3, 6), 2)} exceeds threshold, clipping applied"))
    t.loss = str(loss)
    t.epoch = _epoch(step)

    if t.id == DEMO_TASK_ID:
        # 常驻演示任务：进度封顶 99%，永不结束
        t.progress = min(99, round(step / TOTAL_STEPS * 100)) if step < TOTAL_STEPS else 99
    else:
        t.progress = min(100, round(step / TOTAL_STEPS * 100))
        if step >= TOTAL_STEPS:
            t.status = "success"
            t.progress = 100
            if not t.finishedAt:
                t.finishedAt = _now()   # 供「已耗时」计算（startedAt→finishedAt）
            db.add(TrainLog(task_id=t.id, time=_now(), level="INFO", msg="training finished, best checkpoint saved"))


def _backfill_demo(db, t: TrainTask):
    """把演示任务补到 BACKFILL_POINTS 个点并置为运行中。"""
    t.status = "running"
    cnt = _metric_count(db, t.id)
    for i in range(cnt, BACKFILL_POINTS):
        step = (i + 1) * STEP_PER_TICK
        db.add(TrainMetric(task_id=t.id, step=step, loss=_loss(i), valLoss=_val_loss(i),
                           acc=_acc(i), gpu=random.randint(75, 96)))
    last_step = max(cnt, BACKFILL_POINTS) * STEP_PER_TICK
    t.progress = min(99, round(last_step / TOTAL_STEPS * 100))
    t.epoch = _epoch(last_step)


def _tick():
    db = SessionLocal()
    try:
        running = db.scalars(select(TrainTask).where(TrainTask.status == "running")).all()
        for t in running:
            _advance(db, t)
        db.commit()

        # 保证始终有一个运行中的演示任务
        still_running = db.scalar(select(func.count(TrainTask.id)).where(TrainTask.status == "running")) or 0
        if still_running == 0:
            demo = db.get(TrainTask, DEMO_TASK_ID)
            if demo:
                _backfill_demo(db, demo)
                db.commit()
    finally:
        db.close()


def ensure_demo():
    """启动时保证演示任务运行并有曲线数据。"""
    db = SessionLocal()
    try:
        t = db.get(TrainTask, DEMO_TASK_ID) or db.scalars(select(TrainTask).order_by(TrainTask.id)).first()
        if t:
            _backfill_demo(db, t)
            db.commit()
    finally:
        db.close()


_scheduler: BackgroundScheduler | None = None


def start_scheduler():
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    ensure_demo()
    _scheduler = BackgroundScheduler(timezone=pytz.utc)
    _scheduler.add_job(_tick, "interval", seconds=TICK_SECONDS, id="train_tick",
                       max_instances=1, coalesce=True)
    _scheduler.start()
    print(f"模拟训练调度器已启动（每 {TICK_SECONDS}s 推进一次）", flush=True)
