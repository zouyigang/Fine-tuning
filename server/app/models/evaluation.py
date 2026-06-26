"""模型效果评估模块 ORM 模型。

自动化指标 / 各类别细分 / 基准对比 / 场景验证由下方表落库（可维护、随模型增删），
crud 读表返回；二期真实评估引擎产出后写入同一批表。
"""
from sqlalchemy import Column, Integer, String, Float, Boolean

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


class EvalMetric(Base):
    """自动化指标卡（按模型类型）：metrics 页上半部分。"""
    __tablename__ = "eval_metric"

    id = Column(Integer, primary_key=True, autoincrement=True)
    modelType = Column("model_type", String(32), index=True)
    name = Column(String(32))
    value = Column(Float)
    unit = Column(String(16))
    seq = Column(Integer, default=0)


class EvalPerClass(Base):
    """各类别细分指标（按模型类型）：metrics 页下半部分表格 / 柱状图。"""
    __tablename__ = "eval_per_class"

    id = Column(Integer, primary_key=True, autoincrement=True)
    modelType = Column("model_type", String(32), index=True)
    label = Column(String(32))
    precision = Column("precision_val", Float)
    recall = Column(Float)
    f1 = Column(Float)
    seq = Column(Integer, default=0)


class BenchmarkResult(Base):
    """基准对比（多维 × 多模型）：benchmark 页雷达 + 对比表。"""
    __tablename__ = "benchmark_result"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dim = Column(String(32))
    current = Column("current_val", Float)
    prod = Column("prod_val", Float)
    hist = Column("hist_val", Float)
    seq = Column(Integer, default=0)


class SceneCase(Base):
    """真实业务场景验证案件：scene 页表格；汇总指标由 crud 从案件派生。"""
    __tablename__ = "scene_case"

    id = Column(Integer, primary_key=True, autoincrement=True)
    caseNo = Column("case_no", String(64))
    type = Column(String(32))
    sampleCount = Column("sample_count", Integer)
    accuracy = Column(Float)
    hard = Column(Boolean, default=False)
