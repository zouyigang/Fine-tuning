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
    # 数据集生命周期阶段（权威字段）：待标注→标注中→已标注→已脱敏→已发布→已归档。
    # status 旧字段保留作兼容展示，stage 驱动「导入→标注→脱敏→发布」流水线。
    stage = Column(String(16), default="待标注")
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
    # 可执行掩码类型：idcard/phone/bankcard/name/email/custom；custom 用 pattern(正则)
    maskType = Column("mask_type", String(16), default="custom")
    pattern = Column(String(255))


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


class DatasetType(Base):
    """数据集类型字典（导入页类型下拉的数据源，可启停/排序）。

    value 为英文标识，label 为展示中文（也是写入 dataset.type 的值）。
    enabled=False 的类型不在导入下拉出现。
    """
    __tablename__ = "dataset_type"

    id = Column(Integer, primary_key=True, autoincrement=True)
    value = Column(String(32), unique=True)
    label = Column(String(64))
    seq = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)


class DatasetSample(Base):
    """逐样本主干（P2）：标注/脱敏/发布都作用在它上面。

    raw=导入时的原始行；labeled=标注后结构化字段；masked=脱敏后内容。
    发布时按 masked→labeled→raw 优先级导出为训练文件。
    """
    __tablename__ = "dataset_sample"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, index=True)
    idx = Column(Integer)                 # 行序号
    raw = Column(JSON)                    # 原始行
    labeled = Column(JSON)                # 标注后（未标注为空）
    masked = Column(JSON)                 # 脱敏后（未脱敏为空）
    status = Column(String(16), default="待标注")  # 待标注 / 已标注


class DatasetFile(Base):
    """数据集上传的原始文件记录（物理文件存于 storage/datasets/）。"""
    __tablename__ = "dataset_file"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, index=True)  # 上传时为空，创建数据集后回填
    fileName = Column("file_name", String(255))   # 用户原始文件名
    storedName = Column("stored_name", String(255))  # 磁盘存储名
    size = Column(Integer, default=0)             # 字节数
    rows = Column(Integer, default=0)             # 估算样本量
    uploadedAt = Column("uploaded_at", String(32))
    # 训练文件子类型：同一标注可发布出多份训练集（如「实体关系标注」既能训 NER 又能训关系抽取）。
    # None=单一训练文件；'ner'=命名实体；'relation'=关系三元组。引擎按任务模型类型选对应文件。
    variant = Column(String(16))
    # 训练/验证/测试切分：发布时按比例切分。None=未切分(旧数据，整份)；
    # 'train'=训练集(引擎训练用)；'val'=验证集(LF 验证曲线)；'test'=测试集(评估引擎用)。
    split = Column(String(8))
