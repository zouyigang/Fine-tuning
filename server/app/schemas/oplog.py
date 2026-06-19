"""操作日志出参 Schema。"""
from pydantic import BaseModel, ConfigDict


class OperationLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str | None = None
    realName: str | None = None
    module: str | None = None
    action: str | None = None
    method: str | None = None
    path: str | None = None
    ip: str | None = None
    status: str | None = None
    detail: str | None = None
    time: str | None = None
