"""模型版本管理模块 ORM 模型。"""
from sqlalchemy import Column, Integer, String, Float

from app.core.database import Base


class ModelVersion(Base):
    __tablename__ = "model_version"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64))
    version = Column(String(16))
    modelType = Column("model_type", String(32))
    dataset = Column(String(128))
    f1 = Column(Float)
    size = Column(String(16))
    status = Column(String(16))  # evaluating/evaluated/gray/online/offline/archived
    trainAt = Column("train_at", String(32))
    creator = Column(String(32))
    task_id = Column(Integer, index=True)  # 关联产出该模型的训练任务（真实引擎写入）


class GrayRelease(Base):
    __tablename__ = "gray_release"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64))
    scope = Column(String(128))
    traffic = Column(Integer)
    requests = Column(Integer)
    errorRate = Column("error_rate", Float)
    accuracy = Column(Float)
    status = Column(String(16))
    startAt = Column("start_at", String(32))


class ReleaseHistory(Base):
    __tablename__ = "release_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    version = Column(String(16))
    action = Column(String(16))
    operator = Column(String(32))
    time = Column(String(32))
    status = Column(String(16))
    note = Column(String(255))


class DeployTarget(Base):
    __tablename__ = "deploy_target"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64))
    type = Column(String(16))
    spec = Column(String(64))
    status = Column(String(16))
    load = Column("load_pct", Integer)


class ModelExport(Base):
    """模型导出记录（导出产物存于 storage/models/）。"""
    __tablename__ = "model_export"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, index=True)
    modelName = Column("model_name", String(64))
    version = Column(String(16))
    format = Column(String(16))    # ONNX/TorchScript/...
    quant = Column(String(16))     # none/int8/fp16
    fileName = Column("file_name", String(255))
    storedName = Column("stored_name", String(255))
    size = Column(String(16))
    operator = Column(String(32))
    time = Column(String(32))


class ModelDeployment(Base):
    """模型部署记录（一次「部署到目标环境」对应一条）。"""
    __tablename__ = "model_deployment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, index=True)
    modelName = Column("model_name", String(64))
    version = Column(String(16))
    target_id = Column(Integer)
    targetName = Column("target_name", String(64))
    format = Column(String(16))
    status = Column(String(16))    # 已部署/已下线
    operator = Column(String(32))
    time = Column(String(32))
