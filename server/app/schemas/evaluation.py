"""模型效果评估模块出入参 Schema（字段与前端 evaluation.js 一致）。"""
from pydantic import BaseModel, ConfigDict


class ReportGenIn(BaseModel):
    """生成评估报告入参。"""
    model: str | None = None
    modelType: str | None = None
    sections: list[str] | None = None
    format: str | None = None


class ReviewResultItem(BaseModel):
    id: int
    result: str


class ReviewSubmitIn(BaseModel):
    """批量提交人工复核结果。"""
    results: list[ReviewResultItem] = []


class EvalTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model: str | None = None
    modelType: str | None = None
    dataset: str | None = None
    f1: float | None = None
    precision: float | None = None
    recall: float | None = None
    status: str | None = None
    evalAt: str | None = None


class ReviewSampleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str | None = None
    modelOutput: str | None = None
    reviewer: str | None = None
    result: str | None = None
    reviewedAt: str | None = None


class ErrorCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    errorType: str | None = None
    content: str | None = None
    expected: str | None = None
    actual: str | None = None
    modelType: str | None = None
    count: int | None = 0


class EvalReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None = None
    model: str | None = None
    f1: float | None = None
    conclusion: str | None = None
    creator: str | None = None
    createdAt: str | None = None
    status: str | None = None
