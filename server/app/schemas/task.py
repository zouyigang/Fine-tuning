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
    method: str | None = None
    hyperparams: dict | None = None
    errorMsg: str | None = None
    modelVersionId: int | None = None


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
    # 真实引擎：微调方式 + 超参（{lr,batchSize,epochs,optimizer,maxLen,...}）
    method: str | None = "lora"
    hyperparams: dict | None = None


class StatusIn(BaseModel):
    status: str


class HyperApplyIn(BaseModel):
    """把超参配置应用到指定任务（hyperparams.vue「应用到任务」）。"""
    method: str | None = None
    hyperparams: dict


class ScheduleCreateIn(BaseModel):
    """新建批量调度项入参。"""
    name: str
    priority: str | None = "中"
    gpu: str | None = "待分配"
    scheduledAt: str | None = "立即执行"
    taskId: int | None = None


class ScheduleReorderIn(BaseModel):
    """调度队列重排入参：按 ids 顺序设置 seq。"""
    ids: list[int] = []
