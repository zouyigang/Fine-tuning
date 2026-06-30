"""微调任务管理模块 ORM 模型。"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON

from app.core.database import Base


class TrainTask(Base):
    __tablename__ = "train_task"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    modelType = Column("model_type", String(32))
    baseModel = Column("base_model", String(64))
    dataset = Column(String(128))
    status = Column(String(16), default="pending")  # pending/running/paused/success/failed/stopped
    progress = Column(Integer, default=0)
    priority = Column(String(8), default="中")
    gpu = Column(String(32))
    epoch = Column(String(16))
    loss = Column(String(16), default="-")
    creator = Column(String(32))
    createdAt = Column("created_at", String(32))
    duration = Column(String(32))

    # ---- 真实微调引擎（M1）----
    method = Column(String(16))                       # lora/qlora/full
    hyperparams = Column(JSON)                         # {lr,batchSize,epochs,optimizer,maxLen,...}
    baseModelPath = Column("base_model_path", String(255))  # 解析出的离线权重绝对路径
    outputDir = Column("output_dir", String(255))     # LF 输出目录（含 trainer_log.jsonl）
    pid = Column(Integer)                              # 训练子进程 PID（用于停止）
    errorMsg = Column("error_msg", String(512))       # 失败原因
    modelVersionId = Column("model_version_id", Integer)  # 训练成功后产出的 model_version.id
    startedAt = Column("started_at", String(32))           # 训练真实开始时间（子进程起来时）
    finishedAt = Column("finished_at", String(32))


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


class TaskArtifact(Base):
    """训练产物清单：一个任务可有 adapter（LoRA 增量）/ merged（合并权重）等多条。"""
    __tablename__ = "task_artifact"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, index=True)
    kind = Column(String(16))                 # adapter/merged/checkpoint
    path = Column(String(255))                # 产物绝对/相对路径
    size = Column(String(16))                 # 可读大小
    createdAt = Column("created_at", String(32))


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
