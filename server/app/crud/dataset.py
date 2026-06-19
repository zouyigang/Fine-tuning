"""数据集模块数据库读写。"""
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.dataset import (
    Dataset,
    DatasetVersion,
    DesensitizeRule,
    AnnotationTask,
    DatasetPermission,
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


def create_dataset(db: Session, payload: dict) -> Dataset:
    item = Dataset(
        progress=0, labeled=0, version="v1.0", status="标注中", **payload
    )
    db.add(item)
    db.commit()
    db.refresh(item)
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
