"""微调配置管理模块 ORM 模型。"""
from sqlalchemy import Column, Integer, String, Boolean, Float, JSON

from app.core.database import Base


class BaseModelInfo(Base):
    """基础模型库。"""
    __tablename__ = "base_model"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64))
    source = Column(String(16))  # 开源/原生/第三方
    vendor = Column(String(64))
    params = Column(String(16))
    license = Column("license_name", String(32))
    useCount = Column("use_count", Integer, default=0)
    addedAt = Column("added_at", String(32))
    enabled = Column(Boolean, default=True)


class HyperTemplate(Base):
    """超参模板。"""
    __tablename__ = "hyper_template"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64))
    scene = Column(String(32))
    lr = Column(String(16))
    batchSize = Column("batch_size", Integer)
    epochs = Column(Integer)
    optimizer = Column(String(16))
    useCount = Column("use_count", Integer, default=0)


class ResourceQuota(Base):
    """按部门的训练资源配额。"""
    __tablename__ = "resource_quota"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dept = Column(String(32))
    gpuQuota = Column("gpu_quota", Integer)
    gpuUsed = Column("gpu_used", Integer)
    maxDuration = Column("max_duration", Integer)
    maxConcurrent = Column("max_concurrent", Integer)


class ClusterInfo(Base):
    """集群资源总览（单行）。"""
    __tablename__ = "cluster_info"

    id = Column(Integer, primary_key=True, autoincrement=True)
    totalGpu = Column("total_gpu", Integer)
    usedGpu = Column("used_gpu", Integer)
    totalCpu = Column("total_cpu", Integer)
    usedCpu = Column("used_cpu", Integer)
    runningTasks = Column("running_tasks", Integer)
    queuedTasks = Column("queued_tasks", Integer)


class AutoTuneConfig(Base):
    """自动调优配置（单行）。"""
    __tablename__ = "autotune_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    enabled = Column(Boolean, default=True)
    objective = Column(String(32))
    searchAlgo = Column("search_algo", String(32))
    maxTrials = Column("max_trials", Integer)
    parallelTrials = Column("parallel_trials", Integer)
    searchSpace = Column("search_space", JSON)


class AutoTuneTrial(Base):
    """自动调优试验记录。"""
    __tablename__ = "autotune_trial"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trial = Column(Integer)
    lr = Column(String(16))
    batchSize = Column("batch_size", Integer)
    epochs = Column(Integer)
    f1 = Column(Float)
    status = Column(String(16))


class SysRole(Base):
    """角色及其授予的操作权限（granted 存权限名 JSON 列表）。"""
    __tablename__ = "sys_role"

    id = Column(Integer, primary_key=True, autoincrement=True)
    role = Column(String(32), unique=True)
    granted = Column(JSON)


class PermCatalog(Base):
    """操作权限目录。"""
    __tablename__ = "perm_catalog"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(32), unique=True)
