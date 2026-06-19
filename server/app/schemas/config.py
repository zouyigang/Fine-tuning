"""微调配置管理模块出入参 Schema（字段与前端 config.js 一致）。"""
from pydantic import BaseModel, ConfigDict


class BaseModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None = None
    source: str | None = None
    vendor: str | None = None
    params: str | None = None
    license: str | None = None
    useCount: int | None = 0
    addedAt: str | None = None
    enabled: bool | None = True


class BaseModelIn(BaseModel):
    id: int | None = None
    name: str
    source: str | None = "开源"
    vendor: str | None = None
    params: str | None = None
    license: str | None = None
    addedAt: str | None = None
    enabled: bool | None = True


class HyperTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None = None
    scene: str | None = None
    lr: str | None = None
    batchSize: int | None = 0
    epochs: int | None = 0
    optimizer: str | None = None
    useCount: int | None = 0


class HyperTemplateIn(BaseModel):
    id: int | None = None
    name: str
    scene: str | None = None
    lr: str | None = None
    batchSize: int | None = 16
    epochs: int | None = 8
    optimizer: str | None = "AdamW"


class RolePermIn(BaseModel):
    roles: list[dict] | None = None
