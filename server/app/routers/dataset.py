"""数据集管理接口，路径与前端 src/api/modules/dataset.js 一一对应。

注意：具体路径（/list、/versions 等）声明在 /{ds_id} 之前，避免被动态路由吞掉。
"""
from fastapi import APIRouter, Depends, Query, File, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core import storage
from app.core.database import get_db
from app.core.response import ok, err, page
from app.crud import dataset as crud
from app.deps import get_current_user
from app.models.user import User
from app.schemas.dataset import (
    DatasetOut,
    DatasetCreate,
    VersionOut,
    VersionCreateIn,
    RuleOut,
    AnnotationOut,
    PermissionOut,
    PermissionSaveIn,
    RuleCreateIn,
    RuleToggleIn,
    DesensitizeRunIn,
    DesensitizePreviewIn,
    AnnotationProgressIn,
    AnnotationReviewIn,
    UploadOut,
    DatasetTypeOut,
    DatasetTypeIn,
    DatasetTypeStatusIn,
    SampleOut,
    SampleLabelIn,
)

# 允许的上传文件后缀与大小上限（与前端提示一致：单文件 ≤ 500MB）
_ALLOWED_EXT = (".json", ".jsonl", ".csv", ".txt")
_MAX_SIZE = 500 * 1024 * 1024

router = APIRouter(prefix="/dataset", tags=["dataset"])


@router.get("/list")
def get_dataset_list(
    keyword: str = "",
    type: str = "",
    status: str = "",
    stage: str = "",
    page_no: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="pageSize"),
    db: Session = Depends(get_db),
):
    items, total = crud.list_datasets(db, keyword, type, status, stage, page_no, page_size)
    return ok(page([DatasetOut.model_validate(x) for x in items], total, page_no, page_size))


@router.get("/types")
def get_dataset_types(enabledOnly: bool = True, db: Session = Depends(get_db)):
    """数据集类型字典。enabledOnly=true（默认）供导入下拉/规则表单读启用项；
    管理页传 enabledOnly=false 取全部。"""
    rows = crud.list_dataset_types(db, enabled_only=enabledOnly)
    return ok([DatasetTypeOut.model_validate(r) for r in rows])


@router.post("/types")
def save_dataset_type(payload: DatasetTypeIn, db: Session = Depends(get_db)):
    ok_flag, msg = crud.save_dataset_type(db, payload.model_dump(exclude_none=True))
    if not ok_flag:
        return err(msg, code=4001)
    return ok({"success": True})


@router.put("/types/{type_id}/status")
def set_dataset_type_status(type_id: int, body: DatasetTypeStatusIn, db: Session = Depends(get_db)):
    crud.set_dataset_type_status(db, type_id, body.enabled)
    return ok({"success": True})


@router.delete("/types/{type_id}")
def delete_dataset_type(type_id: int, db: Session = Depends(get_db)):
    ok_flag, msg = crud.delete_dataset_type(db, type_id)
    if not ok_flag:
        return err(msg, code=4001)
    return ok({"success": True})


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


@router.post("/upload")
async def upload_dataset_file(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """本地上传数据集文件：落盘 + 估算样本量，返回 fileId 供创建数据集关联。"""
    name = file.filename or "file"
    if not name.lower().endswith(_ALLOWED_EXT):
        return err("仅支持 JSON / JSONL / CSV / TXT 文件", code=4001)
    data = await file.read()
    if len(data) > _MAX_SIZE:
        return err("单文件不能超过 500MB", code=4001)
    if not data:
        return err("文件内容为空", code=4001)
    stored, abspath, size = storage.save_bytes("datasets", name, data)
    valid, msg, rows = storage.validate_dataset(abspath)
    if not valid:
        # 校验不通过：删除已落盘文件，避免残留
        try:
            import os
            os.remove(abspath)
        except OSError:
            pass
        return err(f"文件格式校验失败：{msg}", code=4001)
    rec = crud.save_dataset_file(db, file_name=name, stored_name=stored, size=size, rows=rows)
    return ok(UploadOut(
        fileId=rec.id, fileName=name, size=size,
        sizeText=storage.human_size(size), rows=rows,
    ))


@router.post("/desensitize-rules")
def create_desensitize_rule(payload: RuleCreateIn, db: Session = Depends(get_db)):
    rule = crud.create_rule(db, payload.model_dump(exclude_none=True))
    return ok(RuleOut.model_validate(rule))


@router.put("/desensitize-rules/{rule_id}")
def toggle_desensitize_rule(rule_id: int, body: RuleToggleIn, db: Session = Depends(get_db)):
    if not crud.toggle_rule(db, rule_id, body.enabled):
        return err("脱敏规则不存在", code=4004)
    return ok({"success": True})


@router.delete("/desensitize-rules/{rule_id}")
def delete_desensitize_rule(rule_id: int, db: Session = Depends(get_db)):
    if not crud.delete_rule(db, rule_id):
        return err("脱敏规则不存在", code=4004)
    return ok({"success": True})


@router.post("/desensitize/preview")
def preview_desensitize(body: DesensitizePreviewIn, db: Session = Depends(get_db)):
    """试脱敏：用当前启用规则对文本脱敏（只读，不落库），供脱敏对比预览。"""
    return ok({"masked": crud.preview_desensitize(db, body.text)})


@router.post("/desensitize/run")
def run_desensitize(body: DesensitizeRunIn, db: Session = Depends(get_db)):
    ok_flag, count = crud.run_desensitize(db, body.datasetId)
    if not ok_flag:
        return err("数据集不存在", code=4004)
    return ok({"success": True, "count": count})


@router.post("/versions")
def create_dataset_version(
    body: VersionCreateIn,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    author = current.real_name or current.username
    v = crud.create_version(db, body.datasetId, body.desc or "", author, body.version)
    if not v:
        return err("数据集不存在", code=4004)
    return ok(VersionOut.model_validate(v))


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


@router.put("/annotation-tasks/{task_id}/review")
def review_annotation(task_id: int, body: AnnotationReviewIn, db: Session = Depends(get_db)):
    """复核标注任务：通过→已完成（数据集进「已标注」可脱敏）；退回→重标。"""
    ok_flag, msg = crud.review_annotation(db, task_id, body.approved)
    if not ok_flag:
        return err(msg, code=4001)
    return ok({"success": True})


@router.delete("/annotation-tasks/{task_id}")
def delete_annotation_task(task_id: int, db: Session = Depends(get_db)):
    """删除标注任务（无下游外键，仅删跟踪行）。"""
    if not crud.delete_annotation_task(db, task_id):
        return err("标注任务不存在", code=4004)
    return ok({"success": True})


@router.post("/permissions")
def save_permissions(payload: PermissionSaveIn, db: Session = Depends(get_db)):
    updated = crud.save_permissions(db, [i.model_dump() for i in payload.items])
    return ok({"updated": updated})


@router.put("/samples/{sample_id}")
def save_sample_label(sample_id: int, body: SampleLabelIn, db: Session = Depends(get_db)):
    """保存一条样本的标注结果（写 labeled、置已标注、重算进度）。"""
    ok_flag, msg = crud.save_sample_label(db, sample_id, body.labeled)
    if not ok_flag:
        return err(msg, code=4004 if msg == "样本不存在" else 4001)
    return ok({"success": True})


@router.get("/{ds_id}/train-data/download")
def download_train_data(ds_id: int, variant: str = "", db: Session = Depends(get_db)):
    """下载该数据集最终训练数据文件（发布后为 alpaca jsonl）。

    variant=ner/relation 时下载对应子类型训练文件（如「实体关系标注」分别产出的
    命名实体 / 关系三元组）；不传或该子类型不存在时回退最新训练文件。
    """
    rec = crud.train_file_by_variant(db, ds_id, variant) if variant else None
    if rec is None:
        rec = crud.latest_dataset_file(db, ds_id)
    if not rec:
        return err("该数据集暂无可下载文件（请先发布）", code=4004)
    abspath = storage.abspath_of("datasets", rec.storedName)
    return storage.file_response(abspath, rec.fileName or f"dataset-{ds_id}.jsonl", "application/jsonl")


@router.get("/{ds_id}/samples")
def get_dataset_samples(
    ds_id: int,
    page_no: int = Query(1, alias="page"),
    page_size: int = Query(10, alias="pageSize"),
    db: Session = Depends(get_db),
):
    """逐样本列表（标注页用），含 raw/labeled/masked/status。"""
    items, total = crud.list_samples(db, ds_id, page_no, page_size)
    return ok(page([SampleOut.model_validate(x) for x in items], total, page_no, page_size))


class PublishIn(BaseModel):
    """发布入参：训练/验证/测试切分比例（百分比，默认 80/10/10）。"""
    trainRatio: int = 80
    valRatio: int = 10
    testRatio: int = 10


@router.post("/{ds_id}/publish")
def publish_dataset(ds_id: int, body: PublishIn | None = None,
                    db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    """发布为可训练数据集：已脱敏 → 已发布 + 定版，并按比例切分 train/val/test。"""
    author = current.real_name or current.username
    b = body or PublishIn()
    ratios = (b.trainRatio, b.valRatio, b.testRatio)
    ok_flag, msg = crud.publish_dataset(db, ds_id, author, ratios=ratios)
    if not ok_flag:
        return err(msg, code=4001)
    return ok({"success": True})


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
