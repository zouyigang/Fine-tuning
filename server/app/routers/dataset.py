"""数据集管理接口，路径与前端 src/api/modules/dataset.js 一一对应。

注意：具体路径（/list、/versions 等）声明在 /{ds_id} 之前，避免被动态路由吞掉。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.response import ok, err, page
from app.crud import dataset as crud
from app.schemas.dataset import (
    DatasetOut,
    DatasetCreate,
    VersionOut,
    RuleOut,
    AnnotationOut,
    PermissionOut,
    PermissionSaveIn,
    RuleCreateIn,
    RuleToggleIn,
    DesensitizeRunIn,
    AnnotationProgressIn,
)

router = APIRouter(prefix="/dataset", tags=["dataset"])


@router.get("/list")
def get_dataset_list(
    keyword: str = "",
    type: str = "",
    status: str = "",
    page_no: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="pageSize"),
    db: Session = Depends(get_db),
):
    items, total = crud.list_datasets(db, keyword, type, status, page_no, page_size)
    return ok(page([DatasetOut.model_validate(x) for x in items], total, page_no, page_size))


@router.get("/desensitize-rules")
def get_desensitize_rules(db: Session = Depends(get_db)):
    rules = crud.get_rules(db)
    return ok([RuleOut.model_validate(x) for x in rules])


@router.get("/annotation-tasks")
def get_annotation_tasks(
    page_no: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="pageSize"),
    db: Session = Depends(get_db),
):
    items, total = crud.list_annotations(db, page_no, page_size)
    return ok(page([AnnotationOut.model_validate(x) for x in items], total, page_no, page_size))


@router.get("/versions")
def get_dataset_versions(datasetId: int | None = None, db: Session = Depends(get_db)):
    items = crud.get_versions(db, datasetId)
    return ok([VersionOut.model_validate(x) for x in items])


@router.get("/statistics")
def get_dataset_statistics(datasetId: int | None = None, db: Session = Depends(get_db)):
    return ok(crud.get_statistics(db, datasetId))


@router.get("/permissions")
def get_dataset_permissions(
    page_no: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="pageSize"),
    db: Session = Depends(get_db),
):
    items, total = crud.list_permissions(db, page_no, page_size)
    return ok(page([PermissionOut.model_validate(x) for x in items], total, page_no, page_size))


@router.post("/desensitize-rules")
def create_desensitize_rule(payload: RuleCreateIn, db: Session = Depends(get_db)):
    rule = crud.create_rule(db, payload.model_dump(exclude_none=True))
    return ok(RuleOut.model_validate(rule))


@router.put("/desensitize-rules/{rule_id}")
def toggle_desensitize_rule(rule_id: int, body: RuleToggleIn, db: Session = Depends(get_db)):
    if not crud.toggle_rule(db, rule_id, body.enabled):
        return err("脱敏规则不存在", code=4004)
    return ok({"success": True})


@router.post("/desensitize/run")
def run_desensitize(body: DesensitizeRunIn, db: Session = Depends(get_db)):
    ok_flag, count = crud.run_desensitize(db, body.datasetId)
    if not ok_flag:
        return err("数据集不存在", code=4004)
    return ok({"success": True, "count": count})


@router.post("/versions/{version_id}/rollback")
def rollback_version(version_id: int, db: Session = Depends(get_db)):
    if not crud.rollback_version(db, version_id):
        return err("版本不存在", code=4004)
    return ok({"success": True})


@router.put("/annotation-tasks/{task_id}/progress")
def update_annotation_progress(task_id: int, body: AnnotationProgressIn, db: Session = Depends(get_db)):
    if not crud.update_annotation_progress(db, task_id, body.done):
        return err("标注任务不存在", code=4004)
    return ok({"success": True})


@router.post("/permissions")
def save_permissions(payload: PermissionSaveIn, db: Session = Depends(get_db)):
    updated = crud.save_permissions(db, [i.model_dump() for i in payload.items])
    return ok({"updated": updated})


@router.get("/{ds_id}")
def get_dataset_detail(ds_id: int, db: Session = Depends(get_db)):
    item = crud.get_dataset(db, ds_id)
    if not item:
        return err("数据集不存在", code=4004)
    return ok(DatasetOut.model_validate(item))


@router.post("")
def create_dataset(payload: DatasetCreate, db: Session = Depends(get_db)):
    item = crud.create_dataset(db, payload.model_dump(exclude_none=True))
    return ok(DatasetOut.model_validate(item))


@router.delete("/{ds_id}")
def delete_dataset(ds_id: int, db: Session = Depends(get_db)):
    crud.delete_dataset(db, ds_id)
    return ok({"success": True})
