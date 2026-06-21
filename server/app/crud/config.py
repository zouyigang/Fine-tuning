"""微调配置管理模块数据库读写。"""
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.config import (
    BaseModelInfo, HyperTemplate, ResourceQuota, ClusterInfo,
    AutoTuneConfig, AutoTuneTrial, SysRole, PermCatalog,
)


# ---- 基础模型库 ----
def list_base_models(db: Session, source: str = "", page: int = 1, page_size: int = 10):
    stmt = select(BaseModelInfo)
    if source:
        stmt = stmt.where(BaseModelInfo.source == source)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(BaseModelInfo.id.desc()).offset((page - 1) * page_size).limit(page_size)
    return db.scalars(stmt).all(), total


def save_base_model(db: Session, payload: dict):
    mid = payload.pop("id", None)
    if mid:
        m = db.get(BaseModelInfo, mid)
        if m:
            for k, v in payload.items():
                setattr(m, k, v)
    else:
        payload.setdefault("addedAt", "2026-06-19")
        m = BaseModelInfo(useCount=0, **payload)
        db.add(m)
    db.commit()


# ---- 超参模板 ----
def list_hyper_templates(db: Session, page: int = 1, page_size: int = 10):
    stmt = select(HyperTemplate)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(HyperTemplate.id.desc()).offset((page - 1) * page_size).limit(page_size)
    return db.scalars(stmt).all(), total


def save_hyper_template(db: Session, payload: dict):
    tid = payload.pop("id", None)
    if tid:
        t = db.get(HyperTemplate, tid)
        if t:
            for k, v in payload.items():
                setattr(t, k, v)
    else:
        t = HyperTemplate(useCount=0, **payload)
        db.add(t)
    db.commit()


def delete_hyper_template(db: Session, tid: int):
    t = db.get(HyperTemplate, tid)
    if t:
        db.delete(t)
        db.commit()


# ---- 训练资源配额 ----
def resource_quotas(db: Session) -> dict:
    c = db.scalars(select(ClusterInfo).limit(1)).first()
    cluster = {
        "totalGpu": c.totalGpu, "usedGpu": c.usedGpu, "totalCpu": c.totalCpu,
        "usedCpu": c.usedCpu, "runningTasks": c.runningTasks, "queuedTasks": c.queuedTasks,
    } if c else {}
    quotas = [
        {"dept": q.dept, "gpuQuota": q.gpuQuota, "gpuUsed": q.gpuUsed,
         "maxDuration": q.maxDuration, "maxConcurrent": q.maxConcurrent}
        for q in db.scalars(select(ResourceQuota).order_by(ResourceQuota.id)).all()
    ]
    return {"cluster": cluster, "quotas": quotas}


def save_resource_quotas(db: Session, quotas: list[dict]) -> int:
    """按部门更新配额（gpuUsed 为实时占用，不在此保存）。返回更新条数。"""
    updated = 0
    for item in quotas:
        q = db.scalars(select(ResourceQuota).where(ResourceQuota.dept == item.get("dept"))).first()
        if not q:
            continue
        if item.get("gpuQuota") is not None:
            q.gpuQuota = item["gpuQuota"]
        if item.get("maxDuration") is not None:
            q.maxDuration = item["maxDuration"]
        if item.get("maxConcurrent") is not None:
            q.maxConcurrent = item["maxConcurrent"]
        updated += 1
    db.commit()
    return updated


# ---- 自动调优配置 ----
def save_autotune_config(db: Session, payload: dict):
    """保存自动调优配置（单行，无则创建）。searchSpace 不在此覆盖。"""
    cfg = db.scalars(select(AutoTuneConfig).limit(1)).first()
    if not cfg:
        cfg = AutoTuneConfig()
        db.add(cfg)
    for k in ("enabled", "objective", "searchAlgo", "maxTrials", "parallelTrials"):
        if payload.get(k) is not None:
            setattr(cfg, k, payload[k])
    db.commit()


def autotune_config(db: Session) -> dict:
    cfg = db.scalars(select(AutoTuneConfig).limit(1)).first()
    trials = [
        {"trial": t.trial, "lr": t.lr, "batchSize": t.batchSize,
         "epochs": t.epochs, "f1": t.f1, "status": t.status}
        for t in db.scalars(select(AutoTuneTrial).order_by(AutoTuneTrial.trial)).all()
    ]
    if not cfg:
        return {"enabled": False, "trials": trials}
    return {
        "enabled": cfg.enabled, "objective": cfg.objective, "searchAlgo": cfg.searchAlgo,
        "maxTrials": cfg.maxTrials, "parallelTrials": cfg.parallelTrials,
        "searchSpace": cfg.searchSpace, "trials": trials,
    }


# ---- 操作权限配置 ----
def role_permissions(db: Session) -> dict:
    perms = [p.name for p in db.scalars(select(PermCatalog).order_by(PermCatalog.id)).all()]
    roles = [
        {"role": r.role, "granted": r.granted or []}
        for r in db.scalars(select(SysRole).order_by(SysRole.id)).all()
    ]
    return {"perms": perms, "roles": roles}


def save_role_permissions(db: Session, roles: list[dict] | None):
    if not roles:
        return
    for item in roles:
        name = item.get("role")
        granted = item.get("granted", [])
        r = db.scalars(select(SysRole).where(SysRole.role == name)).first()
        if r:
            r.granted = granted
        else:
            db.add(SysRole(role=name, granted=granted))
    db.commit()
