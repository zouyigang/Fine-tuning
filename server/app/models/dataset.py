"""数据集管理模块 ORM 模型。

字段命名与前端 mock 数据保持一致（如 updatedAt / canView），
列名用蛇形（updated_at / can_view），借助 Column 的别名映射，
这样 Pydantic from_attributes 可直接读取属性，序列化即为前端所需的 camelCase。
"""
from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON

from app.core.database import Base


class Dataset(Base):
    __tablename__ = "dataset"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    type = Column(String(32))
    dept = Column(String(32))
    total = Column(Integer, default=0)
    labeled = Column(Integer, default=0)
    progress = Column(Integer, default=0)
    version = Column(String(16), default="v1.0")
    desensitized = Column(Boolean, default=False)
    status = Column(String(16), default="标注中")
    owner = Column(String(32))
    updatedAt = Column("updated_at", String(32))
    created_at = Column(DateTime, default=datetime.utcnow)


class DatasetVersion(Base):
    __tablename__ = "dataset_version"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, index=True)
    version = Column(String(16))
    desc = Column("descr", String(255))
    author = Column(String(32))
    count = Column("cnt", Integer)
    current = Column("is_current", Boolean, default=False)
    time = Column(String(32))


class DesensitizeRule(Base):
    __tablename__ = "desensitize_rule"

    id = Column(Integer, primary_key=True, autoincrement=True)
    field = Column(String(32))
    rule = Column(String(128))
    sample = Column(String(128))
    enabled = Column(Boolean, default=True)


class AnnotationTask(Base):
    __tablename__ = "annotation_task"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, index=True)
    title = Column(String(128))
    type = Column(String(32))
    total = Column(Integer)
    done = Column(Integer)
    annotators = Column(Integer)
    status = Column(String(16))
    deadline = Column(String(32))


class DatasetPermission(Base):
    __tablename__ = "dataset_permission"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, index=True)
    name = Column(String(128))
    secret = Column(String(16))
    dept = Column(String(32))
    roles = Column(JSON)
    canView = Column("can_view", Boolean, default=True)
    canEdit = Column("can_edit", Boolean, default=False)
    canExport = Column("can_export", Boolean, default=False)
