"""模型版本管理接口，路径与前端 src/api/modules/model.js 对应。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core import storage
from app.core.database import get_db
from app.core.response import ok, err, page
from app.crud import model_version as crud
from app.deps import get_current_user
from app.models.user import User
from app.schemas.model_version import (
    ModelOut, GrayReleaseOut, ReleaseHistoryOut, DeployTargetOut, StatusIn,
    GrayReleaseIn, TrafficIn, ReleaseIn, RollbackIn,
    ExportIn, ExportOut, DeployIn, BatchIdsIn,
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


@router.post("/gray-releases")
def create_gray_release(body: GrayReleaseIn, db: Session = Depends(get_db)):
    g = crud.create_gray_release(
        db, model_id=body.modelId, name=body.name, scope=body.scope, traffic=body.traffic,
    )
    return ok(GrayReleaseOut.model_validate(g))


@router.put("/gray-releases/{gid}/traffic")
def expand_gray_traffic(gid: int, body: TrafficIn, db: Session = Depends(get_db)):
    if not crud.expand_gray_traffic(db, gid, body.traffic):
        return err("灰度发布不存在", code=4004)
    return ok({"success": True})


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


# ---- 导出 / 部署 / 归档（字面量路径需声明在 /{model_id} 之前）----

@router.get("/exports/{export_id}/download")
def download_export(export_id: int, db: Session = Depends(get_db)):
    rec = crud.get_export(db, export_id)
    if not rec:
        return err("导出记录不存在", code=4004)
    try:
        abspath = storage.abspath_of("models", rec.storedName)
    except ValueError:
        return err("文件路径非法", code=4001)
    return storage.file_response(abspath, rec.fileName)


@router.post("/archive/clean")
def batch_clean_archive(body: BatchIdsIn, db: Session = Depends(get_db)):
    cleaned = crud.archive_clean_batch(db, body.ids)
    return ok({"cleaned": cleaned})


@router.put("/{model_id}/status")
def update_model_status(model_id: int, body: StatusIn, db: Session = Depends(get_db)):
    if not crud.update_status(db, model_id, body.status):
        return err("模型不存在", code=4004)
    return ok({"success": True})


@router.post("/{model_id}/release")
def release_model(
    model_id: int,
    body: ReleaseIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    operator = current.real_name or current.username
    ok_flag, m = crud.release_model(db, model_id, operator, body.note or "")
    if not ok_flag:
        return err("模型不存在", code=4004)
    return ok(ModelOut.model_validate(m))


@router.post("/{model_id}/rollback")
def rollback_model(
    model_id: int,
    body: RollbackIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    operator = current.real_name or current.username
    if not crud.rollback_model(db, model_id, operator, body.note or ""):
        return err("模型不存在", code=4004)
    return ok({"success": True})


@router.post("/{model_id}/export")
def export_model(
    model_id: int,
    body: ExportIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    operator = current.real_name or current.username
    ok_flag, rec = crud.export_model(db, model_id, body.format, body.quant, operator)
    if not ok_flag:
        return err("模型不存在", code=4004)
    return ok(ExportOut.model_validate(rec))


@router.post("/{model_id}/deploy")
def deploy_model(
    model_id: int,
    body: DeployIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    operator = current.real_name or current.username
    ok_flag, logs = crud.deploy_model(db, model_id, body.targetId, body.format, operator)
    if not ok_flag:
        return err("模型或部署目标不存在", code=4004)
    return ok({"logs": logs})


@router.get("/{model_id}/artifacts")
def model_artifacts(model_id: int, db: Session = Depends(get_db)):
    """模型版本关联的真实训练产物（adapter/merged 权重路径与大小）；无则空列表。"""
    arts = crud.real_artifacts(db, model_id)
    return ok([
        {"id": a.id, "kind": a.kind, "path": a.path, "size": a.size, "createdAt": a.createdAt}
        for a in arts
    ])


@router.get("/{model_id}/download")
def download_model(
    model_id: int,
    format: str = "ONNX",
    quant: str = "none",
    db: Session = Depends(get_db),
):
    ok_flag, abspath, name = crud.model_artifact_for_download(db, model_id, format, quant)
    if not ok_flag:
        return err("模型不存在", code=4004)
    return storage.file_response(abspath, name)


@router.post("/{model_id}/clean")
def clean_archive(model_id: int, db: Session = Depends(get_db)):
    ok_flag, msg = crud.archive_clean(db, model_id)
    if not ok_flag:
        return err(msg, code=4003)
    return ok({"success": True, "message": msg})


@router.post("/{model_id}/restore")
def restore_archive(model_id: int, db: Session = Depends(get_db)):
    if not crud.archive_restore(db, model_id):
        return err("模型不存在", code=4004)
    return ok({"success": True})


@router.delete("/{model_id}")
def delete_model(model_id: int, db: Session = Depends(get_db)):
    """删除模型版本（在线/灰度/核心模型拒删；级联清理导出/部署记录、解除任务关联）。"""
    ok_flag, msg = crud.delete_model(db, model_id)
    if not ok_flag:
        return err(msg, code=4001)
    return ok({"success": True})
