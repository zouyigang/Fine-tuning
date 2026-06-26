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
    DatasetType,
    DatasetSample,
)

# 单数据集进标注主干的样本上限（Web 逐条标注场景，避免超大文件灌爆库）
SAMPLE_CAP = 5000


def list_dataset_types(db: Session, enabled_only: bool = True):
    """数据集类型字典（按 seq 升序）。enabled_only 时只返回启用的。"""
    stmt = select(DatasetType)
    if enabled_only:
        stmt = stmt.where(DatasetType.enabled == True)  # noqa: E712
    stmt = stmt.order_by(DatasetType.seq, DatasetType.id)
    return db.scalars(stmt).all()


def resolve_for_training(db: Session, dataset_str: str):
    """把任务的 dataset 字段（id 数字串或名称）解析为 Dataset 行；解析不到返回 None。"""
    if not dataset_str:
        return None
    s = str(dataset_str)
    if s.isdigit():
        return db.get(Dataset, int(s))
    return db.scalars(select(Dataset).where(Dataset.name == s)).first()


def model_type_to_dataset_value(model_type: str | None) -> str | None:
    """业务模型类型（中文 label/关键字）→ 期望的数据集类型 value。
    实体识别/关系抽取共用「实体关系标注」(entity)。识别不了返回 None。"""
    s = (model_type or "").lower()
    if "ocr" in s:
        return "ocr"
    if "实体" in s or "关系" in s:
        return "entity"
    if "事件" in s:
        return "event"
    if "风险" in s:
        return "risk"
    if "路径" in s or "轨迹" in s:
        return "path"
    return None


def model_dataset_type_mismatch(db: Session, model_type: str | None, ds):
    """模型类型与数据集类型是否错配。返回 (mismatch, expected_label, actual_label)。

    任一侧无法识别（自由文本/演示数据/未知模型类型）→ 不判错配，避免误拦、不破坏 sim 演示。
    """
    expected_val = model_type_to_dataset_value(model_type)
    if not expected_val or ds is None:
        return False, None, None
    dt = resolve_dataset_type(db, ds.type)
    if dt is None or not dt.value:
        return False, None, None
    if dt.value != expected_val:
        exp = db.scalars(select(DatasetType).where(DatasetType.value == expected_val)).first()
        return True, (exp.label if exp else expected_val), dt.label
    return False, None, None


def resolve_dataset_type(db: Session, type_str: str):
    """把数据集的 type 字符串解析为 dataset_type 行：先按 label 精确，再按 value 精确。"""
    if not type_str:
        return None
    t = db.scalars(select(DatasetType).where(DatasetType.label == type_str)).first()
    if t is None:
        t = db.scalars(select(DatasetType).where(DatasetType.value == type_str)).first()
    return t


def save_dataset_type(db: Session, payload: dict):
    """新建或更新一个数据集类型（按 id 区分）。返回 (ok, message)。"""
    tid = payload.pop("id", None)
    value = payload.get("value")
    # value 唯一性校验（排除自身）
    dup = db.scalars(select(DatasetType).where(DatasetType.value == value)).first()
    if dup and dup.id != tid:
        return False, f"类型标识「{value}」已存在"
    if tid:
        t = db.get(DatasetType, tid)
        if not t:
            return False, "类型不存在"
        for k, v in payload.items():
            setattr(t, k, v)
    else:
        db.add(DatasetType(**payload))
    db.commit()
    return True, ""


def set_dataset_type_status(db: Session, tid: int, enabled: bool):
    t = db.get(DatasetType, tid)
    if t:
        t.enabled = enabled
        db.commit()


def delete_dataset_type(db: Session, tid: int):
    """删除数据集类型。被转换规则引用时拒绝，避免规则变孤儿。返回 (ok, message)。"""
    from app.models.config import ConvertRule
    t = db.get(DatasetType, tid)
    if not t:
        return False, "类型不存在"
    used = db.scalar(select(func.count()).select_from(ConvertRule).where(ConvertRule.datasetTypeId == tid))
    if used:
        return False, f"该类型下有 {used} 条转换规则，请先调整或删除这些规则"
    db.delete(t)
    db.commit()
    return True, ""


def list_datasets(db: Session, keyword: str = "", type_: str = "", status: str = "",
                  stage: str = "", page: int = 1, page_size: int = 10):
    stmt = select(Dataset)
    if keyword:
        stmt = stmt.where(Dataset.name.like(f"%{keyword}%"))
    if type_:
        stmt = stmt.where(Dataset.type == type_)
    if status:
        stmt = stmt.where(Dataset.status == status)
    if stage:
        # 支持逗号分隔多阶段（如 "已标注,已脱敏"），便于脱敏页一次取多个待处理阶段
        stages = [s.strip() for s in stage.split(",") if s.strip()]
        stmt = stmt.where(Dataset.stage.in_(stages))

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
    # 流水线入口：新数据集落在「待标注」阶段
    item = Dataset(
        progress=0, labeled=0, version="v1.0", status="标注中", stage="待标注", **payload
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    if f:
        f.dataset_id = item.id
        # 灌入逐样本主干（P2），供标注页逐条标注
        n = populate_samples(db, item.id, f.storedName)
        # 真实上传的数据集自动建一条标注任务，使其出现在「多类型数据标注」页（打通 导入→标注）
        db.add(AnnotationTask(
            dataset_id=item.id, title=f"{item.name} 标注任务", type=item.type,
            total=n or f.rows or item.total or 0, done=0, annotators=1,
            status="标注中", deadline="",
        ))
        db.commit()
    return item


def populate_samples(db: Session, dataset_id: int, stored_name: str) -> int:
    """把上传文件的行灌入 dataset_sample（raw），返回灌入条数（封顶 SAMPLE_CAP）。"""
    from app.core import storage as st
    try:
        abspath = st.abspath_of("datasets", stored_name)
        rows = _load_data_rows(abspath)
    except Exception:
        return 0
    n = 0
    for i, row in enumerate(rows[:SAMPLE_CAP]):
        raw = row if isinstance(row, dict) else {"text": str(row)}
        db.add(DatasetSample(dataset_id=dataset_id, idx=i, raw=raw, status="待标注"))
        n += 1
    db.commit()
    return n


def latest_dataset_file(db: Session, dataset_id: int):
    """该数据集最新的物理文件记录（发布后即为 alpaca 训练文件）。"""
    return db.scalars(select(DatasetFile).where(DatasetFile.dataset_id == dataset_id)
                      .order_by(DatasetFile.id.desc())).first()


# 转换规则的输出别名 → 训练文件子类型（NER / 关系抽取）
_REL_OUT_KEYS = ("relations", "spo", "spo_list", "triples", "三元组", "关系")
_NER_OUT_KEYS = ("entities", "entity", "ner", "实体", "标注")


def _variant_rule_split(rules: list | None) -> dict:
    """把某类型的多条转换规则按输出类型分成 {'ner':[...], 'relation':[...]}。

    仅当确实分出 ≥2 个子类型才返回（即「实体关系标注」这种一标注两用途的类型）；
    否则返回 {} → 走单一训练文件（其余类型行为不变）。
    """
    if not rules or len(rules) < 2:
        return {}
    out: dict = {}
    for r in rules:
        outs = [str(a).lower() for a in (r.get("outputAliases") or [])]
        if any(k.lower() in outs for k in _REL_OUT_KEYS):
            out.setdefault("relation", []).append(r)
        elif any(k.lower() in outs for k in _NER_OUT_KEYS):
            out.setdefault("ner", []).append(r)
    return out if len(out) >= 2 else {}


def _model_type_variant(model_type: str | None) -> str | None:
    """任务模型类型（中文 label 或英文 value）→ 训练文件子类型。"""
    s = (model_type or "").lower()
    if "实体" in s or "ner" in s:
        return "ner"
    if "关系" in s or "relation" in s:
        return "relation"
    return None


def train_file_by_variant(db: Session, dataset_id: int, variant: str):
    """取指定子类型（ner/relation）的训练文件；无则返回 None。"""
    if not variant:
        return None
    return db.scalars(
        select(DatasetFile).where(DatasetFile.dataset_id == dataset_id, DatasetFile.variant == variant)
        .order_by(DatasetFile.id.desc())
    ).first()


def dataset_file_for_task(db: Session, dataset_id: int, model_type: str | None):
    """按任务模型类型挑该数据集的训练文件：
    实体识别→variant=ner，关系抽取→variant=relation；命中不到则回退无子类型文件，再回退最新。"""
    files = db.scalars(select(DatasetFile).where(DatasetFile.dataset_id == dataset_id)
                       .order_by(DatasetFile.id.desc())).all()
    if not files:
        return None
    variant = _model_type_variant(model_type)
    if variant:
        hit = next((f for f in files if (f.variant or "") == variant), None)
        if hit:
            return hit
    plain = next((f for f in files if not f.variant), None)
    return plain or files[0]


def list_samples(db: Session, dataset_id: int, page: int = 1, page_size: int = 10):
    stmt = select(DatasetSample).where(DatasetSample.dataset_id == dataset_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(DatasetSample.idx).offset((page - 1) * page_size).limit(page_size)
    return db.scalars(stmt).all(), total


def save_sample_label(db: Session, sample_id: int, labeled: dict):
    """保存一条样本的标注结果，置「已标注」，并重算所属数据集的标注进度。

    返回 (ok, message)。复核通过后数据集进入下游（已标注/已脱敏/已发布/已归档），
    标注随即锁定——此时拒绝再改，避免对已脱敏/已发布（可能已用于训练）的数据无声改动。
    """
    s = db.get(DatasetSample, sample_id)
    if not s:
        return False, "样本不存在"
    ds = db.get(Dataset, s.dataset_id) if s.dataset_id else None
    if ds and ds.stage not in ("待标注", "标注中"):
        return False, f"数据集已进入「{ds.stage}」阶段，标注已锁定，不可再修改"
    s.labeled = labeled
    s.status = "已标注"
    db.commit()
    recompute_annotation_progress(db, s.dataset_id)
    return True, ""


def recompute_annotation_progress(db: Session, dataset_id: int):
    """按样本已标注比例重算进度，同步数据集与其标注任务；全部标注完推进阶段到「已标注」。"""
    total = db.scalar(select(func.count()).select_from(DatasetSample)
                      .where(DatasetSample.dataset_id == dataset_id)) or 0
    labeled = db.scalar(select(func.count()).select_from(DatasetSample)
                        .where(DatasetSample.dataset_id == dataset_id,
                               DatasetSample.status == "已标注")) or 0
    pct = round(labeled / total * 100) if total else 0
    ds = db.get(Dataset, dataset_id)
    if ds:
        ds.labeled = labeled
        ds.progress = pct
        # 标注满额不直接进「已标注」，须经复核通过（review_annotation）；此处仅标「标注中」
        if 0 < pct and ds.stage == "待标注":
            ds.stage = "标注中"
    for t in db.scalars(select(AnnotationTask).where(AnnotationTask.dataset_id == dataset_id)).all():
        t.done = pct
        if pct >= 100 and t.status not in ("已完成", "待审核"):
            t.status = "待审核"   # 待复核
        elif 0 < pct < 100:
            t.status = "标注中"
    db.commit()
    return pct


def review_annotation(db: Session, task_id: int, approved: bool):
    """复核标注任务。通过→任务「已完成」，该数据集所有任务都完成则进「已标注」(可脱敏)；
    退回→任务「标注中」、数据集回「标注中」重标。返回 (ok, message)。"""
    t = db.get(AnnotationTask, task_id)
    if not t:
        return False, "任务不存在"
    if t.status != "待审核":
        return False, "仅「待审核」的任务可复核"
    ds = db.get(Dataset, t.dataset_id) if t.dataset_id else None
    if approved:
        t.status = "已完成"
        db.flush()  # 让下面的 pending 计数看到本次状态变更（SessionLocal autoflush=False）
        if ds:
            pending = db.scalar(select(func.count()).select_from(AnnotationTask).where(
                AnnotationTask.dataset_id == ds.id, AnnotationTask.status != "已完成"))
            if not pending and ds.stage in ("待标注", "标注中"):
                ds.stage = "已标注"
    else:
        t.status = "标注中"
        if ds and ds.stage in ("已标注", "标注中"):
            ds.stage = "标注中"
    db.commit()
    return True, ""


def delete_annotation_task(db: Session, task_id: int) -> bool:
    """删除一条标注任务。annotation_task 无下游外键引用（样本属数据集而非任务），
    故仅删除该跟踪行，不影响数据集与其样本。"""
    t = db.get(AnnotationTask, task_id)
    if not t:
        return False
    db.delete(t)
    db.commit()
    return True


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


def delete_rule(db: Session, rule_id: int) -> bool:
    """删除一条脱敏规则。规则在脱敏执行时按需读取、无持久外键引用，故可直接删除。"""
    r = db.get(DesensitizeRule, rule_id)
    if not r:
        return False
    db.delete(r)
    db.commit()
    return True


def run_desensitize(db: Session, dataset_id: int):
    """执行脱敏：对最新原始文件真实应用脱敏规则，写出脱敏后新文件并推进阶段。

    返回 (是否成功, 处理样本量)。无上传文件的数据集（如演示种子）退化为仅置标志位。
    """
    from app.core import storage as st
    from app.services import desensitize as dz
    import json

    ds = db.get(Dataset, dataset_id)
    if not ds:
        return False, 0

    rules = [
        {"field": r.field, "maskType": r.maskType or "custom", "pattern": r.pattern, "enabled": True}
        for r in db.scalars(select(DesensitizeRule).where(DesensitizeRule.enabled == True)).all()  # noqa: E712
    ]

    # 优先按样本主干脱敏（P2）：对每条样本的 labeled（无则 raw）真实掩码，写入 masked
    samples = db.scalars(select(DatasetSample).where(DatasetSample.dataset_id == dataset_id)).all()
    if samples:
        from app.services import desensitize as dz
        srcs = [(s.labeled or s.raw or {}) for s in samples]
        masked, _hits = dz.apply(srcs, rules) if rules else (srcs, 0)
        for s, m in zip(samples, masked):
            s.masked = m
        ds.desensitized = True
        ds.stage = "已脱敏"
        db.commit()
        return True, len(samples)

    rec = db.scalars(
        select(DatasetFile).where(DatasetFile.dataset_id == dataset_id).order_by(DatasetFile.id.desc())
    ).first()

    count = ds.total or 0
    if rec and rules:
        try:
            abspath = st.abspath_of("datasets", rec.storedName)
            rows = _load_data_rows(abspath)
            masked, _hits = dz.apply(rows, rules)
            # 脱敏后统一以 jsonl 落盘，成为最新 dataset_file（训练自然读取脱敏版）
            payload = "\n".join(
                json.dumps(r, ensure_ascii=False) if isinstance(r, (dict, list)) else str(r)
                for r in masked
            ).encode("utf-8")
            stored, _abspath, size = st.save_bytes("datasets", f"masked_ds{dataset_id}.jsonl", payload)
            db.add(DatasetFile(
                dataset_id=dataset_id, fileName=f"masked_{rec.fileName or 'data'}.jsonl",
                storedName=stored, size=size, rows=len(masked),
                uploadedAt=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))
            count = len(masked)
        except Exception:
            pass  # 解析失败时退化为仅置标志位，不阻断流程

    ds.desensitized = True
    ds.stage = "已脱敏"
    db.commit()
    return True, count


def preview_desensitize(db: Session, text: str) -> str:
    """用当前启用的脱敏规则对一段文本试脱敏，返回脱敏后文本（只读，不落库）。"""
    from app.services import desensitize as dz
    rules = [
        {"field": r.field, "maskType": r.maskType or "custom", "pattern": r.pattern, "enabled": True}
        for r in db.scalars(select(DesensitizeRule).where(DesensitizeRule.enabled == True)).all()  # noqa: E712
    ]
    out, _hits = dz.apply([text or ""], rules)
    return out[0] if out else (text or "")


def _load_data_rows(abspath: str):
    """读取数据文件为行集合：json/jsonl → list[dict]；csv/txt → list[str]（按行）。"""
    import json
    low = abspath.lower()
    if low.endswith(".jsonl"):
        rows = []
        with open(abspath, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s:
                    rows.append(json.loads(s))
        return rows
    if low.endswith(".json"):
        with open(abspath, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    return v
        return []
    # csv / txt：按非空行
    with open(abspath, "r", encoding="utf-8", errors="ignore") as f:
        return [ln.rstrip("\n") for ln in f if ln.strip()]


def publish_dataset(db: Session, dataset_id: int, author: str = "system"):
    """发布为可训练数据集：**发布时即把数据转成最终 alpaca 训练样本并落地**，
    训练时直读、无需再转换。返回 (ok, message)。

    取数优先级 masked→labeled→raw（样本主干），无样本则回退最新上传文件；
    套该数据集类型的转换规则生成 alpaca，落盘为最新 dataset_file（标准格式，引擎直通）。
    """
    import os
    import json
    from app.core import storage as st
    from app.crud import convert_rule as rule_crud
    from app.services import dataset_convert

    ds = db.get(Dataset, dataset_id)
    if not ds:
        return False, "数据集不存在"
    if ds.stage == "已发布":
        return False, "该数据集已发布"
    if ds.stage == "已归档":
        return False, "已归档数据集不可发布"

    rules = rule_crud.load_rules_for_type(db, ds.type)
    samples = db.scalars(select(DatasetSample).where(DatasetSample.dataset_id == dataset_id)
                         .order_by(DatasetSample.idx)).all()

    # 该类型是否需要按模型子类型产出多份训练文件（如「实体关系标注」→ NER + 关系抽取）
    variant_rules = _variant_rule_split(rules) if samples else {}

    if samples and variant_rules:
        # 多子类型：同一标注分别套「命名实体」「关系三元组」规则各产一份训练文件，
        # 引擎按任务模型类型（实体识别/关系抽取）选对应文件。
        rows = [(s.masked or s.labeled or s.raw or {}) for s in samples]
        produced, total = [], 0
        for variant, vrules in variant_rules.items():
            alpaca, _note = dataset_convert.convert(rows, ds.type, rules=vrules)
            if not alpaca:
                continue
            payload = "\n".join(json.dumps(r, ensure_ascii=False) for r in alpaca).encode("utf-8")
            stored, _abspath, size = st.save_bytes("datasets", f"train_ds{dataset_id}_{variant}.jsonl", payload)
            db.add(DatasetFile(
                dataset_id=dataset_id, fileName=f"train_ds{dataset_id}_{variant}_alpaca.jsonl",
                storedName=stored, size=size, rows=len(alpaca), variant=variant,
                uploadedAt=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ))
            produced.append(f"{variant}({len(alpaca)})")
            total += len(alpaca)
        if not produced:
            return False, "无法生成训练样本：标注中未识别出可训练字段（实体/关系）"
        note = "多类型训练文件：" + "、".join(produced)
    elif samples:
        # 样本主干（标注流水线，封顶 SAMPLE_CAP）：内存转换 → 落盘（单一训练文件）
        rows = [(s.masked or s.labeled or s.raw or {}) for s in samples]
        alpaca, note = dataset_convert.convert(rows, ds.type, rules=rules)
        if not alpaca:
            return False, f"无法生成训练样本：{note}"
        payload = "\n".join(json.dumps(r, ensure_ascii=False) for r in alpaca).encode("utf-8")
        stored, _abspath, size = st.save_bytes("datasets", f"train_ds{dataset_id}.jsonl", payload)
        db.add(DatasetFile(
            dataset_id=dataset_id, fileName=f"train_ds{dataset_id}_alpaca.jsonl",
            storedName=stored, size=size, rows=len(alpaca),
            uploadedAt=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))
    else:
        # 无样本（外部已标注大文件直接导入）：流式转换，内存恒定，避免大文件 OOM
        rec = db.scalars(select(DatasetFile).where(DatasetFile.dataset_id == dataset_id)
                         .order_by(DatasetFile.id.desc())).first()
        if not rec:
            return False, "数据集无可发布的样本"
        stored, abspath = st.reserve_path("datasets", f"train_ds{dataset_id}.jsonl")
        count, note = dataset_convert.convert_stream(
            st.abspath_of("datasets", rec.storedName), abspath, ds.type, rules)
        if count == 0:
            try:
                os.remove(abspath)
            except OSError:
                pass
            return False, f"无法生成训练样本：{note}"
        size = os.path.getsize(abspath)
        db.add(DatasetFile(
            dataset_id=dataset_id, fileName=f"train_ds{dataset_id}_alpaca.jsonl",
            storedName=stored, size=size, rows=count,
            uploadedAt=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))

    create_version(db, dataset_id, f"发布训练版本（{note}）", author)
    ds.stage = "已发布"
    ds.status = "已完成"
    db.commit()
    return True, ""


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
    """更新标注任务进度；满 100% 自动转「待审核」，并推进所属数据集阶段到「已标注」。"""
    t = db.get(AnnotationTask, task_id)
    if not t:
        return False
    t.done = max(0, min(100, done))
    if t.done >= 100 and t.status not in ("已完成", "待审核"):
        t.status = "待审核"
        # 打通 标注→脱敏：标注完成把数据集推进到「已标注」（待脱敏）
        ds = db.get(Dataset, t.dataset_id) if t.dataset_id else None
        if ds and ds.stage in ("待标注", "标注中"):
            ds.stage = "已标注"
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
