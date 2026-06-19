"""模型效果评估模块 ORM 模型。

注：基准对比 / 自动化指标 / 场景验证等多为聚合分析结果，
由接口实时计算返回，不单独建实体表（见后续 service 层）。
"""
from sqlalchemy import Column, Integer, String, Float

from app.core.database import Base


class EvalTask(Base):
    __tablename__ = "eval_task"

    id = Column(Integer, primary_key=True, autoincrement=True)
    model = Column(String(64))
    modelType = Column("model_type", String(32))
    dataset = Column(String(128))
    f1 = Column(Float)
    precision = Column("precision_val", Float)
    recall = Column(Float)
    status = Column(String(16))
    evalAt = Column("eval_at", String(32))


class EvalReport(Base):
    __tablename__ = "eval_report"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128))
    model = Column(String(64))
    f1 = Column(Float)
    conclusion = Column(String(32))
    creator = Column(String(32))
    createdAt = Column("created_at", String(32))
    status = Column(String(16))


class ReviewSample(Base):
    __tablename__ = "review_sample"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(String(512))
    modelOutput = Column("model_output", String(512))
    reviewer = Column(String(32))
    result = Column(String(16))
    reviewedAt = Column("reviewed_at", String(32))


class ErrorCase(Base):
    __tablename__ = "error_case"

    id = Column(Integer, primary_key=True, autoincrement=True)
    errorType = Column("error_type", String(32))
    content = Column(String(512))
    expected = Column(String(255))
    actual = Column(String(255))
    modelType = Column("model_type", String(32))
    count = Column("cnt", Integer)
