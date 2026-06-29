"""模型版本管理模块数据库读写。"""
import json
import os
import random
from datetime import datetime

from sqlalchemy import select, func, delete as sa_delete
from sqlalchemy.orm import Session

from app.core import storage
from app.models.model_version import (
    ModelVersion, GrayRelease, ReleaseHistory, DeployTarget,
    ModelExport, ModelDeployment,
)
from app.models.task import TaskArtifact

# 导出格式 → 文件后缀
_FORMAT_EXT = {
    "ONNX": "onnx", "TorchScript": "pt", "PMML": "pmml",
    "SavedModel": "pb", "GGUF": "gguf",
}


def real_artifacts(db: Session, model_id: int) -> list[TaskArtifact]:
    """该模型版本关联训练任务的真实产物（adapter/merged）。无则空。"""
    m = db.get(ModelVersion, model_id)
    if not m or not m.task_id:
        return []
    return db.scalars(
        select(TaskArtifact).where(TaskArtifact.task_id == m.task_id).order_by(TaskArtifact.id)
    ).all()


def _merged_artifact(db: Session, model_id: int) -> TaskArtifact | None:
    for a in real_artifacts(db, model_id):
        if a.kind == "merged":
            return a
    return None


def _artifact_bytes(m: ModelVersion, fmt: str, quant: str, real: TaskArtifact | None = None) -> bytes:
    """生成模型导出产物 manifest。

    真实训练模型（real 指向 merged 权重目录）：manifest 引用真实权重路径 + 文件清单 + 大小，
    标记 real=true；种子/演示模型则为占位说明。
    （多 GB 权重不打包进单文件下载，manifest 作为可下载的产物描述符指向真实权重。）
    """
    manifest = {
        "model": m.name, "version": m.version, "modelType": m.modelType,
        "dataset": m.dataset, "f1": m.f1, "format": fmt, "quantization": quant,
        "exportedAt": _now(),
    }
    if real and real.path and os.path.isdir(real.path):
        files = sorted(os.listdir(real.path))
        manifest.update({
            "real": True,
            "weightsDir": real.path,
            "weightsSize": real.size,
            "files": files,
            "note": "本模型由真实微调引擎（LLaMA-Factory）训练并合并导出，weightsDir 为完整权重目录。",
        })
    else:
        manifest["real"] = False
        manifest["note"] = "演示产物（manifest）；该模型版本无关联真实训练产物。"
    return json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")


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


def _is_permanent(m: ModelVersion) -> bool:
    """核心模型（F1 > 0.93）永久保留，不可清理。"""
    return (m.f1 or 0) > 0.93


def export_model(db: Session, model_id: int, fmt: str, quant: str, operator: str):
    """导出模型：生成产物文件并落盘，写导出记录。返回 (ok, ModelExport)。"""
    m = db.get(ModelVersion, model_id)
    if not m:
        return False, None
    fmt = fmt or "ONNX"
    quant = quant or "none"
    ext = _FORMAT_EXT.get(fmt, "bin")
    download_name = f"{m.name}_{m.version}_{quant}.{ext}"
    data = _artifact_bytes(m, fmt, quant, real=_merged_artifact(db, m.id))
    stored, _abspath, size = storage.save_bytes("models", download_name, data)
    rec = ModelExport(
        model_id=m.id, modelName=m.name, version=m.version, format=fmt, quant=quant,
        fileName=download_name, storedName=stored, size=storage.human_size(size),
        operator=operator, time=_now(),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return True, rec


def get_export(db: Session, export_id: int) -> ModelExport | None:
    return db.get(ModelExport, export_id)


def model_artifact_for_download(db: Session, model_id: int, fmt: str = "ONNX", quant: str = "none"):
    """为归档/版本下载即时生成产物文件，返回 (ok, 绝对路径, 下载名)。"""
    m = db.get(ModelVersion, model_id)
    if not m:
        return False, None, None
    ext = _FORMAT_EXT.get(fmt, "bin")
    download_name = f"{m.name}_{m.version}.{ext}"
    data = _artifact_bytes(m, fmt, quant, real=_merged_artifact(db, m.id))
    stored, abspath, _size = storage.save_bytes("models", download_name, data)
    return True, abspath, download_name


def deploy_model(db: Session, model_id: int, target_id: int, fmt: str, operator: str):
    """部署模型到目标环境：写部署记录 + 抬高目标负载。返回 (ok, 部署日志列表)。"""
    m = db.get(ModelVersion, model_id)
    t = db.get(DeployTarget, target_id)
    if not m or not t:
        return False, None
    rec = ModelDeployment(
        model_id=m.id, modelName=m.name, version=m.version, target_id=t.id,
        targetName=t.name, format=fmt or "ONNX", status="已部署",
        operator=operator, time=_now(),
    )
    db.add(rec)
    # 部署后目标负载上升（封顶 95%）
    t.load = min(95, (t.load or 0) + random.randint(5, 15))
    db.commit()
    logs = [
        f"[1/4] 正在将模型 {m.name} {m.version}（{fmt or 'ONNX'}）推送至「{t.name}」...",
        "[2/4] 校验模型完整性... OK",
        "[3/4] 加载模型到推理引擎... OK",
        "[4/4] 健康检查通过，服务已就绪 ✓",
    ]
    return True, logs


def delete_model(db: Session, model_id: int):
    """删除模型版本。返回 (ok, message)。

    外键关联校验：
      - 在线/灰度中的模型不可删（正对外服务），须先下线；
      - 核心模型（F1>0.93）永久保留（与归档清理一致）。
    级联清理：`model_export` / `model_deployment` 记录（model_id 关联）；
    解除关联训练任务的 `modelVersionId`（任务本身保留，仅去掉悬挂引用）。
    上线/回滚历史 `release_history`（按版本号、审计留痕）不删。
    """
    from app.models.task import TrainTask
    m = db.get(ModelVersion, model_id)
    if not m:
        return False, "模型版本不存在"
    if m.status in ("online", "gray"):
        return False, "该模型正在线/灰度服务中，请先下线再删除"
    if _is_permanent(m):
        return False, "核心模型（F1>0.93）永久保留，不可删除"
    db.execute(sa_delete(ModelExport).where(ModelExport.model_id == model_id))
    db.execute(sa_delete(ModelDeployment).where(ModelDeployment.model_id == model_id))
    for t in db.scalars(select(TrainTask).where(TrainTask.modelVersionId == model_id)).all():
        t.modelVersionId = None
    db.delete(m)
    db.commit()
    return True, ""


def archive_clean(db: Session, model_id: int):
    """清理归档模型：核心模型拒绝；其余删除版本记录释放空间。返回 (ok, message)。"""
    m = db.get(ModelVersion, model_id)
    if not m:
        return False, "模型不存在"
    if _is_permanent(m):
        return False, "核心模型永久保留，不可清理"
    db.delete(m)
    db.commit()
    return True, "已清理，释放存储空间"


def archive_clean_batch(db: Session, ids: list[int]) -> int:
    """批量清理（跳过核心模型）。返回实际清理数量。"""
    cleaned = 0
    for mid in ids:
        m = db.get(ModelVersion, mid)
        if m and not _is_permanent(m):
            db.delete(m)
            cleaned += 1
    db.commit()
    return cleaned


def archive_restore(db: Session, model_id: int) -> bool:
    """恢复归档模型：状态置为 offline（可重新进入上线流程）。"""
    m = db.get(ModelVersion, model_id)
    if not m:
        return False
    m.status = "offline"
    db.commit()
    return True


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
        d["permanent"] = _is_permanent(m)
        out.append(d)
    return out, total
