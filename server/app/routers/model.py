"""模型版本管理接口，路径与前端 src/api/modules/model.js 对应。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok, err, page
from app.crud import model_version as crud
from app.schemas.model_version import (
    ModelOut, GrayReleaseOut, ReleaseHistoryOut, DeployTargetOut, StatusIn,
)

router = APIRouter(prefix="/model", tags=["model"])


@router.get("/list")
def get_model_list(
    keyword: str = "",
    status: str = "",
    modelType: str = "",
    page_no: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="pageSize"),
    db: Session = Depends(get_db),
):
    items, total = crud.list_models(db, keyword, status, modelType, page_no, page_size)
    return ok(page([ModelOut.model_validate(x) for x in items], total, page_no, page_size))


@router.get("/gray-releases")
def get_gray_releases(db: Session = Depends(get_db)):
    return ok([GrayReleaseOut.model_validate(x) for x in crud.gray_releases(db)])


@router.get("/gray-trend")
def get_gray_trend():
    return ok(crud.gray_trend())


@router.get("/release-history")
def get_release_history(db: Session = Depends(get_db)):
    return ok([ReleaseHistoryOut.model_validate(x) for x in crud.release_history(db)])


@router.get("/rollback-candidates")
def get_rollback_candidates(db: Session = Depends(get_db)):
    return ok(crud.rollback_candidates(db))


@router.get("/deploy-targets")
def get_deploy_targets(db: Session = Depends(get_db)):
    return ok([DeployTargetOut.model_validate(x) for x in crud.deploy_targets(db)])


@router.get("/archive")
def get_archive_list(
    page_no: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="pageSize"),
    db: Session = Depends(get_db),
):
    items, total = crud.archive_list(db, page_no, page_size)
    return ok(page(items, total, page_no, page_size))


@router.put("/{model_id}/status")
def update_model_status(model_id: int, body: StatusIn, db: Session = Depends(get_db)):
    if not crud.update_status(db, model_id, body.status):
        return err("模型不存在", code=4004)
    return ok({"success": True})
