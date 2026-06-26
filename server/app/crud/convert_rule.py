"""数据转换规则（convert_rule）读写 + 供引擎按类型加载规则 + 试转换预览。

方案2：规则归属到某个数据集类型（dataset_type.id）。DB 匹配按 FK，不再靠关键字子串。
"""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.config import ConvertRule
from app.models.dataset import DatasetType
from app.crud import dataset as ds_crud
from app.services import dataset_convert


def _to_dict(r: ConvertRule) -> dict:
    """ORM → 引擎/转换器期望的规则字典（camelCase 键）。"""
    return {
        "id": r.id,
        "datasetTypeId": r.datasetTypeId,
        "typeMatch": r.typeMatch or "",
        "name": r.name or "",
        "priority": r.priority if r.priority is not None else 100,
        "instruction": r.instruction or "",
        "inputAliases": r.inputAliases or [],
        "outputAliases": r.outputAliases or [],
        "outputFormat": r.outputFormat or "text",
        "enabled": bool(r.enabled),
    }


def list_rules(db: Session) -> list:
    """全部规则（启用在前、按 priority 升序），附带所属类型 label，供管理页展示。"""
    rows = db.scalars(select(ConvertRule)).all()
    rows.sort(key=lambda r: (not bool(r.enabled), r.priority if r.priority is not None else 100, r.id))
    type_label = {t.id: t.label for t in db.scalars(select(DatasetType)).all()}
    out = []
    for r in rows:
        d = _to_dict(r)
        d["datasetTypeLabel"] = type_label.get(r.datasetTypeId) or ""
        out.append(d)
    return out


def load_rules_for_type(db: Session, ds_type_str: str):
    """供引擎/预览：解析数据集 type → 该类型的启用规则（按 priority 升序）。

    解析不到类型或该类型无规则时返回 None，约定调用方回退内置 DEFAULT_RULES（按子串）。
    """
    t = ds_crud.resolve_dataset_type(db, ds_type_str)
    if t is None:
        return None
    rows = db.scalars(
        select(ConvertRule).where(ConvertRule.datasetTypeId == t.id, ConvertRule.enabled == True)  # noqa: E712
    ).all()
    if not rows:
        return None
    rows.sort(key=lambda r: r.priority if r.priority is not None else 100)
    return [_to_dict(r) for r in rows]


def save_rule(db: Session, payload: dict):
    """新建或更新一条规则（按 id 区分）。"""
    rid = payload.pop("id", None)
    if rid:
        r = db.get(ConvertRule, rid)
        if r:
            for k, v in payload.items():
                setattr(r, k, v)
    else:
        r = ConvertRule(**payload)
        db.add(r)
    db.commit()


def delete_rule(db: Session, rid: int):
    r = db.get(ConvertRule, rid)
    if r:
        db.delete(r)
        db.commit()


def set_enabled(db: Session, rid: int, enabled: bool):
    r = db.get(ConvertRule, rid)
    if r:
        r.enabled = enabled
        db.commit()


def preview(db: Session, sample_text: str, ds_type: str | None) -> dict:
    """试转换：把用户粘贴的原始样本（JSON 对象 / 数组 / JSONL）按该类型的规则转一遍。

    返回 {samples, note, error}；error 非空表示输入无法解析。
    """
    text = (sample_text or "").strip()
    if not text:
        return {"samples": [], "note": "", "error": "请粘贴原始样本数据"}
    rows = None
    try:
        parsed = json.loads(text)
        rows = parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        # 退而当作 JSONL（每行一个对象）
        rows = []
        for ln in text.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                rows.append(json.loads(ln))
            except json.JSONDecodeError:
                return {"samples": [], "note": "", "error": f"无法解析为 JSON / JSONL：{ln[:50]}"}
    samples, note = dataset_convert.convert(rows, ds_type, rules=load_rules_for_type(db, ds_type))
    return {"samples": samples, "note": note, "error": ""}
