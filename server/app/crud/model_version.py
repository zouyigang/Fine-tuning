"""模型版本管理模块数据库读写。"""
import random
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.model_version import ModelVersion, GrayRelease, ReleaseHistory, DeployTarget


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def list_models(db: Session, keyword: str = "", status: str = "", model_type: str = "",
                page: int = 1, page_size: int = 10):
    stmt = select(ModelVersion)
    if keyword:
        stmt = stmt.where(ModelVersion.name.like(f"%{keyword}%"))
    if status:
        stmt = stmt.where(ModelVersion.status == status)
    if model_type:
        stmt = stmt.where(ModelVersion.modelType == model_type)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(ModelVersion.id.desc()).offset((page - 1) * page_size).limit(page_size)
    return db.scalars(stmt).all(), total


def update_status(db: Session, model_id: int, status: str) -> bool:
    m = db.get(ModelVersion, model_id)
    if not m:
        return False
    m.status = status
    db.commit()
    return True


def gray_releases(db: Session):
    return db.scalars(select(GrayRelease).order_by(GrayRelease.id)).all()


def create_gray_release(db: Session, *, model_id: int | None, name: str | None,
                        scope: str | None, traffic: int):
    """新建灰度发布；若关联了具体模型则把它置为 gray。"""
    title = name
    if model_id:
        m = db.get(ModelVersion, model_id)
        if m:
            title = title or f"{m.name} {m.version}"
            m.status = "gray"
    g = GrayRelease(
        name=title or "未命名灰度发布", scope=scope or "-", traffic=traffic,
        requests=0, errorRate=0.0, accuracy=0.0, status="灰度中", startAt=_now(),
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


def expand_gray_traffic(db: Session, gid: int, traffic: int) -> bool:
    g = db.get(GrayRelease, gid)
    if not g:
        return False
    g.traffic = max(0, min(100, traffic))
    db.commit()
    return True


def release_model(db: Session, model_id: int, operator: str, note: str = ""):
    """全量上线：目标模型置 online，同类型原在线模型降为 offline，并写上线记录。"""
    m = db.get(ModelVersion, model_id)
    if not m:
        return False, None
    prev = db.scalars(
        select(ModelVersion).where(
            ModelVersion.modelType == m.modelType,
            ModelVersion.status == "online",
            ModelVersion.id != m.id,
        )
    ).all()
    for p in prev:
        p.status = "offline"
    m.status = "online"
    db.add(ReleaseHistory(
        version=m.version, action="全量上线", operator=operator, time=_now(),
        status="成功", note=note or f"{m.name} {m.version} 全量上线",
    ))
    db.commit()
    db.refresh(m)
    return True, m


def rollback_model(db: Session, model_id: int, operator: str, note: str = "") -> bool:
    """快速回滚：目标模型置 online，同类型原在线模型降为 offline，并写回滚记录。"""
    m = db.get(ModelVersion, model_id)
    if not m:
        return False
    cur = db.scalars(
        select(ModelVersion).where(
            ModelVersion.modelType == m.modelType,
            ModelVersion.status == "online",
            ModelVersion.id != m.id,
        )
    ).all()
    for c in cur:
        c.status = "offline"
    m.status = "online"
    db.add(ReleaseHistory(
        version=m.version, action="回滚", operator=operator, time=_now(),
        status="成功", note=note or f"回滚至 {m.name} {m.version}",
    ))
    db.commit()
    return True


def gray_trend() -> dict:
    return {
        "points": [f"{i * 2}:00" for i in range(12)],
        "accuracy": [round(random.uniform(91, 95), 1) for _ in range(12)],
        "errorRate": [round(random.uniform(0.3, 1.5), 2) for _ in range(12)],
    }


def release_history(db: Session):
    return db.scalars(select(ReleaseHistory).order_by(ReleaseHistory.id)).all()


def rollback_candidates(db: Session):
    rows = db.scalars(
        select(ModelVersion).where(ModelVersion.status.in_(["online", "offline"])).limit(6)
    ).all()
    out = []
    for m in rows:
        d = {c: getattr(m, c) for c in ("id", "name", "version", "modelType", "dataset",
                                        "f1", "size", "status", "trainAt", "creator")}
        d["stable"] = (m.f1 or 0) > 0.9
        out.append(d)
    return out


def deploy_targets(db: Session):
    return db.scalars(select(DeployTarget).order_by(DeployTarget.id)).all()


def archive_list(db: Session, page: int = 1, page_size: int = 10):
    stmt = select(ModelVersion).where(ModelVersion.status.in_(["offline", "archived"]))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(
        stmt.order_by(ModelVersion.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    out = []
    for m in rows:
        d = {c: getattr(m, c) for c in ("id", "name", "version", "modelType", "dataset",
                                        "f1", "size", "status", "trainAt", "creator")}
        d["archivedAt"] = f"2026-05-{random.randint(10, 28)}"
        d["permanent"] = (m.f1 or 0) > 0.93
        out.append(d)
    return out, total
