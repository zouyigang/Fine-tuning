"""M2：业务原始数据集 → LLaMA-Factory 指令样本（alpaca {instruction,input,output}）。

公安五类业务数据（数据集 type 字段，中文 label）各有一套字段约定，但实际上传的
字段名不统一，故每类用「字段别名」宽松识别，缺字段的行跳过。识别不了的类型走
通用兜底（两字段对/常见问答键）。返回 (alpaca样本列表, 统计说明)。

设计为纯函数 + 数据驱动，便于单测与后续扩展新业务类型。
"""
import json


def _first(row: dict, *aliases):
    """按别名顺序取第一个非空值。"""
    for a in aliases:
        if a in row and row[a] not in (None, "", [], {}):
            return row[a]
    return None


def _as_text(v) -> str:
    if isinstance(v, str):
        return v
    return json.dumps(v, ensure_ascii=False)


def _json(v) -> str:
    return json.dumps(v, ensure_ascii=False)


# ---- 各业务类型：row -> alpaca 或 None ----

def _conv_ocr(row: dict):
    raw = _first(row, "raw", "ocr", "ocr_text", "source", "text", "原文", "识别文本")
    fixed = _first(row, "corrected", "fixed", "correct", "target", "output", "校对", "正确文本", "校对后")
    if raw is None or fixed is None:
        return None
    return {
        "instruction": "请校对并改正下面 OCR 识别文本中的错别字、漏字与格式错误，输出正确文本。",
        "input": _as_text(raw),
        "output": _as_text(fixed),
    }


def _conv_entity(row: dict):
    text = _first(row, "text", "sentence", "content", "文本", "原文", "句子")
    if text is None:
        return None
    # 关系三元组优先
    rels = _first(row, "relations", "spo", "spo_list", "triples", "关系", "三元组")
    if rels is not None:
        return {
            "instruction": "抽取下列文本中的实体关系三元组（主体、关系、客体），以 JSON 数组输出。",
            "input": _as_text(text),
            "output": _json(rels),
        }
    ents = _first(row, "entities", "entity", "ner", "labels", "实体", "标注")
    if ents is not None:
        return {
            "instruction": "抽取下列文本中的命名实体（人名/地点/机构/时间/金额等），以 JSON 输出。",
            "input": _as_text(text),
            "output": _json(ents),
        }
    return None


def _conv_event(row: dict):
    text = _first(row, "text", "sentence", "content", "文本", "原文")
    events = _first(row, "events", "event_list", "event", "事件", "事件列表")
    if text is None or events is None:
        return None
    return {
        "instruction": "识别下列文本中的事件类型、触发词及论元角色，以 JSON 输出。",
        "input": _as_text(text),
        "output": _json(events),
    }


def _conv_risk(row: dict):
    text = _first(row, "text", "content", "sentence", "文本", "内容", "原文")
    label = _first(row, "label", "risk", "risk_type", "risk_level", "category", "风险", "风险类型", "标签", "类别")
    if text is None or label is None:
        return None
    return {
        "instruction": "判断下列内容的风险类型/等级，直接输出风险标签。",
        "input": _as_text(text),
        "output": _as_text(label),
    }


def _conv_generic(row: dict):
    """通用兜底：常见问答键对，或恰好两个字符串字段视为 输入→输出。"""
    q = _first(row, "question", "input", "prompt", "query", "问题", "问")
    a = _first(row, "answer", "output", "response", "completion", "回答", "答")
    if q is not None and a is not None:
        return {"instruction": _as_text(q), "input": "", "output": _as_text(a)}
    str_items = [(k, v) for k, v in row.items() if isinstance(v, str) and v.strip()]
    if len(str_items) == 2:
        return {"instruction": _as_text(str_items[0][1]), "input": "", "output": _as_text(str_items[1][1])}
    return None


# 数据集 type（中文 label / value）→ 转换器
_BY_TYPE = [
    (("ocr", "OCR"), _conv_ocr),
    (("entity", "实体", "关系"), _conv_entity),
    (("event", "事件"), _conv_event),
    (("risk", "风险"), _conv_risk),
]


def _converter_for(ds_type: str):
    t = ds_type or ""
    for keys, fn in _BY_TYPE:
        if any(k in t for k in keys):
            return fn
    return None


def convert(rows: list, ds_type: str | None) -> tuple[list, str]:
    """把业务原始 rows 转成 alpaca 样本列表。

    先按数据集类型选专用转换器，逐行转换；专用转换器对某行失败时回退通用兜底。
    返回 (samples, note)。samples 为空表示无法转换（note 说明原因）。
    """
    if not rows or not isinstance(rows[0], dict):
        return [], "数据为空或非对象数组，无法转换"
    primary = _converter_for(ds_type)
    samples, skipped = [], 0
    for row in rows:
        if not isinstance(row, dict):
            skipped += 1
            continue
        s = (primary(row) if primary else None) or _conv_generic(row)
        if s and s.get("output"):
            samples.append(s)
        else:
            skipped += 1
    if not samples:
        kind = f"「{ds_type}」" if ds_type else ""
        return [], f"未能从{kind}数据集识别出可训练字段（已尝试专用+通用转换，跳过 {skipped} 行）"
    note = f"类型={ds_type or '通用'}，转换 {len(samples)} 条" + (f"，跳过 {skipped} 条" if skipped else "")
    return samples, note
