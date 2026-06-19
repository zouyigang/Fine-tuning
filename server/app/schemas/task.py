"""微调任务模块出入参 Schema。"""
from pydantic import BaseModel, ConfigDict


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    modelType: str | None = None
    baseModel: str | None = None
    dataset: str | None = None
    status: str | None = None
    progress: int | None = 0
    priority: str | None = None
    gpu: str | None = None
    epoch: str | None = None
    loss: str | None = None
    creator: str | None = None
    createdAt: str | None = None
    duration: str | None = None


class TaskCreate(BaseModel):
    name: str
    modelType: str | None = None
    baseModel: str | None = None
    dataset: str | None = None
    priority: str | None = "中"
    gpu: str | None = None
    epoch: str | None = None
    creator: str | None = None
    createdAt: str | None = None
    duration: str | None = None


class StatusIn(BaseModel):
    status: str
