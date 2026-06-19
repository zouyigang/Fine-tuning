"""模型版本管理模块出入参 Schema（字段与前端 model.js 一致）。"""
from pydantic import BaseModel, ConfigDict


class ModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None = None
    version: str | None = None
    modelType: str | None = None
    dataset: str | None = None
    f1: float | None = None
    size: str | None = None
    status: str | None = None
    trainAt: str | None = None
    creator: str | None = None


class GrayReleaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None = None
    scope: str | None = None
    traffic: int | None = 0
    requests: int | None = 0
    errorRate: float | None = None
    accuracy: float | None = None
    status: str | None = None
    startAt: str | None = None


class ReleaseHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    version: str | None = None
    action: str | None = None
    operator: str | None = None
    time: str | None = None
    status: str | None = None
    note: str | None = None


class DeployTargetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None = None
    type: str | None = None
    spec: str | None = None
    status: str | None = None
    load: int | None = 0


class StatusIn(BaseModel):
    status: str
