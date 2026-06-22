"""微调任务管理模块 ORM 模型。"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime

from app.core.database import Base


class TrainTask(Base):
    __tablename__ = "train_task"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    modelType = Column("model_type", String(32))
    baseModel = Column("base_model", String(64))
    dataset = Column(String(128))
    status = Column(String(16), default="pending")  # pending/running/paused/success/failed
    progress = Column(Integer, default=0)
    priority = Column(String(8), default="中")
    gpu = Column(String(32))
    epoch = Column(String(16))
    loss = Column(String(16), default="-")
    creator = Column(String(32))
    createdAt = Column("created_at", String(32))
    duration = Column(String(32))


class TrainMetric(Base):
    """训练曲线时序点（P4 模拟训练写入）。"""
    __tablename__ = "train_metric"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, index=True)
    step = Column(Integer)
    loss = Column(Float)
    valLoss = Column("val_loss", Float)
    acc = Column(Float)
    gpu = Column(Integer)
    ts = Column(DateTime, default=datetime.utcnow)


class TrainLog(Base):
    __tablename__ = "train_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, index=True)
    time = Column(String(32))
    level = Column(String(8))
    msg = Column(String(512))


class ScheduleItem(Base):
    """批量调度队列项：持久化排队顺序 / 优先级 / 计划执行时间。

    与 train_task 解耦：调度队列可独立增删、排序，不影响训练任务本体。
    task_id 可关联已存在的训练任务（为空表示纯调度占位）。
    """
    __tablename__ = "schedule_item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, index=True, nullable=True)
    name = Column(String(128))
    priority = Column(String(8), default="中")
    status = Column(String(16), default="pending")
    gpu = Column(String(32))
    seq = Column(Integer, default=0)               # 排队顺序（小在前）
    scheduledAt = Column("scheduled_at", String(32))
