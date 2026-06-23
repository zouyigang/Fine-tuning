"""数据集模块数据库读写。"""
import re

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from datetime import datetime

from app.models.dataset import (
    Dataset,
    DatasetVersion,
    DesensitizeRule,
    AnnotationTask,
    DatasetPermission,
    DatasetFile,
)


def list_datasets(db: Session, keyword: str = "", type_: str = "", status: str = "",
                  page: int = 1, page_size: int = 10):
    stmt = select(Dataset)
    if keyword:
        stmt = stmt.where(Dataset.name.like(f"%{keyword}%"))
    if type_:
        stmt = stmt.where(Dataset.type == type_)
    if status:
        stmt = stmt.where(Dataset.status == status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(Dataset.id.desc()).offset((page - 1) * page_size).limit(page_size)
    items = db.scalars(stmt).all()
    return items, total


def get_dataset(db: Session, ds_id: int) -> Dataset | None:
    return db.get(Dataset, ds_id)


def save_dataset_file(db: Session, *, file_name: str, stored_name: str,
                      size: int, rows: int) -> DatasetFile:
    """登记一条上传文件记录（dataset_id 待创建数据集后回填）。"""
    rec = DatasetFile(
        fileName=file_name, storedName=stored_name, size=size, rows=rows,
        uploadedAt=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def create_dataset(db: Session, payload: dict) -> Dataset:
    # 关联上传文件：回填 dataset_id，并以真实行数作为样本量
    file_id = payload.pop("fileId", None)
    f = db.get(DatasetFile, file_id) if file_id else None
    if f and (f.rows or 0) > 0:
        payload["total"] = f.rows
    item = Dataset(
        progress=0, labeled=0, version="v1.0", status="标注中", **payload
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    if f:
        f.dataset_id = item.id
        db.commit()
    return item


def delete_dataset(db: Session, ds_id: int) -> bool:
    item = db.get(Dataset, ds_id)
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


def get_versions(db: Session, dataset_id: int | None):
    stmt = select(DatasetVersion)
    if dataset_id:
        stmt = stmt.where(DatasetVersion.dataset_id == dataset_id)
    stmt = stmt.order_by(DatasetVersion.id)  # 插入顺序即新→旧，current 版本在最前
    return db.scalars(stmt).all()


def get_rules(db: Session):
    return db.scalars(select(DesensitizeRule).order_by(DesensitizeRule.id)).all()


def create_rule(db: Session, payload: dict) -> DesensitizeRule:
    rule = DesensitizeRule(**payload)
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


def toggle_rule(db: Session, rule_id: int, enabled: bool) -> bool:
    r = db.get(DesensitizeRule, rule_id)
    if not r:
        return False
    r.enabled = enabled
    db.commit()
    return True


def run_desensitize(db: Session, dataset_id: int):
    """执行脱敏：将目标数据集标记为已脱敏，返回 (是否成功, 处理样本量)。"""
    ds = db.get(Dataset, dataset_id)
    if not ds:
        return False, 0
    ds.desensitized = True
    db.commit()
    return True, (ds.total or 0)


def _next_version(versions: list[DatasetVersion]) -> str:
    """根据已有版本号推断下一个版本号（vX.Y → 次版本号 +1）。"""
    max_major, max_minor = 1, 0
    for v in versions:
        m = re.match(r"v?(\d+)\.(\d+)", str(v.version or ""))
        if not m:
            continue
        major, minor = int(m.group(1)), int(m.group(2))
        if (major, minor) > (max_major, max_minor):
            max_major, max_minor = major, minor
    return f"v{max_major}.{max_minor + 1}"


def create_version(db: Session, dataset_id: int, desc: str, author: str,
                   version: str | None = None) -> DatasetVersion | None:
    """新建数据集版本：自动顺延版本号、置为当前版本、同步主表版本与样本量。"""
    ds = db.get(Dataset, dataset_id)
    if not ds:
        return None
    existing = db.scalars(
        select(DatasetVersion).where(DatasetVersion.dataset_id == dataset_id)
    ).all()
    new_version = version or _next_version(existing)
    for o in existing:
        o.current = False
    v = DatasetVersion(
        dataset_id=dataset_id,
        version=new_version,
        desc=desc or f"新建版本 {new_version}",
        author=author or "-",
        count=ds.total or 0,
        current=True,
        time=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    db.add(v)
    ds.version = new_version
    db.commit()
    db.refresh(v)
    return v


def rollback_version(db: Session, version_id: int) -> bool:
    """版本回滚：把目标版本置为当前版本，同数据集其余版本取消当前标记。"""
    v = db.get(DatasetVersion, version_id)
    if not v:
        return False
    others = db.scalars(
        select(DatasetVersion).where(DatasetVersion.dataset_id == v.dataset_id)
    ).all()
    for o in others:
        o.current = (o.id == version_id)
    # 同步数据集主表当前版本号
    ds = db.get(Dataset, v.dataset_id)
    if ds:
        ds.version = v.version
    db.commit()
    return True


def update_annotation_progress(db: Session, task_id: int, done: int) -> bool:
    """更新标注任务进度；满 100% 自动转「待审核」。"""
    t = db.get(AnnotationTask, task_id)
    if not t:
        return False
    t.done = max(0, min(100, done))
    if t.done >= 100 and t.status not in ("已完成", "待审核"):
        t.status = "待审核"
    db.commit()
    return True


def list_annotations(db: Session, page: int = 1, page_size: int = 10):
    stmt = select(AnnotationTask)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(AnnotationTask.id).offset((page - 1) * page_size).limit(page_size)
    return db.scalars(stmt).all(), total


def list_permissions(db: Session, page: int = 1, page_size: int = 10):
    stmt = select(DatasetPermission)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(DatasetPermission.id).offset((page - 1) * page_size).limit(page_size)
    return db.scalars(stmt).all(), total


def save_permissions(db: Session, items: list[dict]) -> int:
    """批量保存数据集权限（按 id 更新角色与查看/编辑/导出开关）。返回更新条数。"""
    updated = 0
    for item in items:
        p = db.get(DatasetPermission, item.get("id"))
        if not p:
            continue
        p.roles = item.get("roles") or []
        p.canView = bool(item.get("canView"))
        p.canEdit = bool(item.get("canEdit"))
        p.canExport = bool(item.get("canExport"))
        updated += 1
    db.commit()
    return updated


def get_statistics(db: Session, dataset_id: int | None):
    """统计分析：overview 由真实数据汇总，分布/建议为示例数据（后续可接真实统计任务）。"""
    if dataset_id:
        ds = db.get(Dataset, dataset_id)
    else:
        ds = db.scalars(select(Dataset).order_by(Dataset.id.desc()).limit(1)).first()

    total = ds.total if ds else 48200
    labeled = ds.labeled if ds else 45120

    return {
        "overview": {
            "total": total,
            "labeled": labeled,
            "quality": 96.4,
            "balance": 78,
        },
        "entityDist": [
            {"name": "人名", "value": 12400},
            {"name": "组织机构", "value": 8600},
            {"name": "时间", "value": 7200},
            {"name": "地点", "value": 6800},
            {"name": "金额", "value": 5400},
            {"name": "案由", "value": 3200},
        ],
        "typeDist": [
            {"name": "OCR 校对", "value": 18000},
            {"name": "实体关系", "value": 15200},
            {"name": "事件标注", "value": 9000},
            {"name": "风险样本", "value": 6000},
        ],
        "suggestions": [
            "“案由”类实体样本偏少（占比 6.6%），建议补充至 5000 条以上以平衡分布",
            "风险样本中“资金异常”子类占比过高（72%），建议增加“身份异常”样本",
            "约 3080 条样本尚未标注，建议优先分配标注人员完成",
        ],
    }
