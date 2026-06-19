"""微调配置管理接口，路径与前端 src/api/modules/config.js 对应。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok, page
from app.crud import config as crud
from app.schemas.config import (
    BaseModelOut, BaseModelIn, HyperTemplateOut, HyperTemplateIn, RolePermIn,
)

router = APIRouter(prefix="/config", tags=["config"])


# ---- 基础模型库 ----
@router.get("/base-models")
def get_base_models(
    source: str = "",
    page_no: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="pageSize"),
    db: Session = Depends(get_db),
):
    items, total = crud.list_base_models(db, source, page_no, page_size)
    return ok(page([BaseModelOut.model_validate(x) for x in items], total, page_no, page_size))


@router.post("/base-models")
def save_base_model(payload: BaseModelIn, db: Session = Depends(get_db)):
    crud.save_base_model(db, payload.model_dump(exclude_none=True))
    return ok({"success": True})


# ---- 超参模板 ----
@router.get("/hyper-templates")
def get_hyper_templates(
    page_no: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="pageSize"),
    db: Session = Depends(get_db),
):
    items, total = crud.list_hyper_templates(db, page_no, page_size)
    return ok(page([HyperTemplateOut.model_validate(x) for x in items], total, page_no, page_size))


@router.post("/hyper-templates")
def save_hyper_template(payload: HyperTemplateIn, db: Session = Depends(get_db)):
    crud.save_hyper_template(db, payload.model_dump(exclude_none=True))
    return ok({"success": True})


@router.delete("/hyper-templates/{tid}")
def delete_hyper_template(tid: int, db: Session = Depends(get_db)):
    crud.delete_hyper_template(db, tid)
    return ok({"success": True})


# ---- 训练资源配额 ----
@router.get("/resource-quotas")
def get_resource_quotas(db: Session = Depends(get_db)):
    return ok(crud.resource_quotas(db))


# ---- 自动调优配置 ----
@router.get("/autotune")
def get_autotune_config(db: Session = Depends(get_db)):
    return ok(crud.autotune_config(db))


# ---- 操作权限配置 ----
@router.get("/role-permissions")
def get_role_permissions(db: Session = Depends(get_db)):
    return ok(crud.role_permissions(db))


@router.post("/role-permissions")
def save_role_permissions(payload: RolePermIn, db: Session = Depends(get_db)):
    crud.save_role_permissions(db, payload.roles)
    return ok({"success": True})
