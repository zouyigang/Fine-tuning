"""M2：业务原始数据集 → LLaMA-Factory 指令样本（alpaca {instruction,input,output}）。

公安五类业务数据（数据集 type 字段，中文 label）各有一套字段约定，但实际上传的
字段名不统一，故每类用「字段别名」宽松识别，缺字段的行跳过。识别不了的类型走
通用兜底（两字段对/常见问答键）。返回 (alpaca样本列表, 统计说明)。

设计为「规则数据 + 纯函数」：转换规则可由数据库 `convert_rule` 表驱动（页面维护），
未传规则时回退内置 DEFAULT_RULES（与历史硬编码转换器等价，保证离线/单测行为不变）。
通用兜底 _conv_generic 保留在代码内（其 instruction 取自数据本身，不适合配置化）。
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


# ---- 内置默认规则（等价于历史硬编码的 OCR/实体/事件/风险 转换器）----
# 字段名用 camelCase，与 convert_rule 表 / crud 返回结构一致。
# datasetTypeValue：种子建表时据此把规则关联到 dataset_type（方案2 FK）。
# typeMatch：仅本文件离线兜底（无 DB 时按子串选规则）用；DB 路径不再用它匹配。
DEFAULT_RULES = [
    {
        "datasetTypeValue": "ocr", "typeMatch": "ocr", "name": "OCR 校对", "priority": 10, "outputFormat": "text",
        "instruction": "请校对并改正下面 OCR 识别文本中的错别字、漏字与格式错误，输出正确文本。",
        "inputAliases": ["raw", "ocr", "ocr_text", "source", "text", "原文", "识别文本"],
        "outputAliases": ["corrected", "fixed", "correct", "target", "output", "校对", "正确文本", "校对后"],
        "enabled": True,
    },
    {
        "datasetTypeValue": "entity", "typeMatch": "实体,关系", "name": "实体-关系三元组", "priority": 10, "outputFormat": "json",
        "instruction": "抽取下列文本中的实体关系三元组（主体、关系、客体），以 JSON 数组输出。",
        "inputAliases": ["text", "sentence", "content", "文本", "原文", "句子"],
        "outputAliases": ["relations", "spo", "spo_list", "triples", "关系", "三元组"],
        "enabled": True,
    },
    {
        "datasetTypeValue": "entity", "typeMatch": "实体,关系", "name": "实体-命名实体", "priority": 20, "outputFormat": "json",
        "instruction": "抽取下列文本中的命名实体（人名/地点/机构/时间/金额等），以 JSON 输出。",
        "inputAliases": ["text", "sentence", "content", "文本", "原文", "句子"],
        "outputAliases": ["entities", "entity", "ner", "labels", "实体", "标注"],
        "enabled": True,
    },
    {
        "datasetTypeValue": "event", "typeMatch": "事件", "name": "事件抽取", "priority": 10, "outputFormat": "json",
        "instruction": "识别下列文本中的事件类型、触发词及论元角色，以 JSON 输出。",
        "inputAliases": ["text", "sentence", "content", "文本", "原文"],
        "outputAliases": ["events", "event_list", "event", "事件", "事件列表"],
        "enabled": True,
    },
    {
        "datasetTypeValue": "risk", "typeMatch": "风险", "name": "风险分类", "priority": 10, "outputFormat": "text",
        "instruction": "判断下列内容的风险类型/等级，直接输出风险标签。",
        "inputAliases": ["text", "content", "sentence", "文本", "内容", "原文"],
        "outputAliases": ["label", "risk", "risk_type", "risk_level", "category", "风险", "风险类型", "标签", "类别"],
        "enabled": True,
    },
    {
        "datasetTypeValue": "path", "typeMatch": "路径,轨迹,path", "name": "路径还原研判", "priority": 10, "outputFormat": "text",
        "instruction": "根据下列时空轨迹点（时间-地点序列），还原嫌疑人活动路径并给出研判结论。",
        "inputAliases": ["轨迹", "trajectory", "track", "points", "轨迹点", "时空轨迹", "text", "原文"],
        "outputAliases": ["路径分析", "研判", "分析", "结论", "path", "route", "轨迹分析", "output"],
        "enabled": True,
    },
]


def _kw_list(s: str) -> list:
    """把逗号分隔（中/英文逗号兼容）的匹配关键字拆成列表。"""
    return [k.strip() for k in (s or "").replace("，", ",").split(",") if k.strip()]


def _rule_matches(rule: dict, ds_type: str) -> bool:
    """规则任一关键字（忽略大小写）为数据集类型子串即命中。"""
    t = (ds_type or "").lower()
    return any(k.lower() in t for k in _kw_list(rule.get("typeMatch")))


def _apply_rule(row: dict, rule: dict):
    """按规则的别名/格式从一行原始数据生成 alpaca 样本；字段缺失返回 None。"""
    out = _first(row, *(rule.get("outputAliases") or []))
    if out is None:
        return None
    in_aliases = rule.get("inputAliases") or []
    inp = _first(row, *in_aliases) if in_aliases else ""
    if in_aliases and inp is None:   # 配了输入别名却取不到 → 该规则不适用此行
        return None
    fmt = (rule.get("outputFormat") or "text").lower()
    output = _json(out) if fmt == "json" else _as_text(out)
    return {
        "instruction": rule.get("instruction") or "",
        "input": _as_text(inp) if inp not in (None, "") else "",
        "output": output,
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


def select_default_rules(ds_type: str | None) -> list:
    """无 DB 规则时的离线兜底：按 typeMatch 子串从内置 DEFAULT_RULES 选规则（按 priority 升序）。"""
    return sorted(
        [r for r in DEFAULT_RULES if r.get("enabled", True) and _rule_matches(r, ds_type)],
        key=lambda r: r.get("priority", 100),
    )


def apply_rules(rows: list, rules: list, ds_type: str | None = None) -> tuple[list, str]:
    """对已筛选并排好序的 rules，逐行依次尝试，第一条字段都取到的生效；都不适用走通用兜底。"""
    samples, skipped = [], 0
    for row in rows:
        if not isinstance(row, dict):
            skipped += 1
            continue
        s = None
        for r in rules:
            s = _apply_rule(row, r)
            if s and s.get("output"):
                break
            s = None
        if s is None:
            s = _conv_generic(row)
        if s and s.get("output"):
            samples.append(s)
        else:
            skipped += 1
    if not samples:
        kind = f"「{ds_type}」" if ds_type else ""
        return [], f"未能从{kind}数据集识别出可训练字段（已尝试 {len(rules)} 条规则+通用兜底，跳过 {skipped} 行）"
    note = (f"类型={ds_type or '通用'}，命中规则 {len(rules)} 条，转换 {len(samples)} 条"
            + (f"，跳过 {skipped} 条" if skipped else ""))
    return samples, note


def _resolve_rules(ds_type, rules):
    if rules is None:
        return select_default_rules(ds_type)
    return sorted([r for r in rules if r.get("enabled", True)], key=lambda r: r.get("priority", 100))


def _convert_row(row: dict, rules: list):
    """单行 → alpaca（命中规则优先，否则通用兜底）；失败返回 None。"""
    if not isinstance(row, dict):
        return None
    s = None
    for r in rules:
        s = _apply_rule(row, r)
        if s and s.get("output"):
            return s
        s = None
    g = _conv_generic(row)
    return g if (g and g.get("output")) else None


def convert_stream(in_path: str, out_path: str, ds_type: str | None, rules: list | None = None) -> tuple[int, str]:
    """流式把 jsonl 业务文件逐行转成 alpaca jsonl，内存恒定（大数据不 OOM）。

    仅对 .jsonl 流式；其它格式（json 数组/csv/txt）回退到内存版 convert（这些通常不至超大）。
    返回 (条数, 说明)。
    """
    import json as _json
    if not in_path.lower().endswith(".jsonl"):
        rows = _read_rows_mem(in_path)
        samples, note = convert(rows, ds_type, rules)
        with open(out_path, "w", encoding="utf-8") as f:
            for s in samples:
                f.write(_json.dumps(s, ensure_ascii=False) + "\n")
        return len(samples), note

    matching = _resolve_rules(ds_type, rules)
    count = skipped = 0
    with open(in_path, "r", encoding="utf-8") as fin, open(out_path, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                row = _json.loads(line)
            except _json.JSONDecodeError:
                skipped += 1
                continue
            s = _convert_row(row, matching)
            if s:
                fout.write(_json.dumps(s, ensure_ascii=False) + "\n")
                count += 1
            else:
                skipped += 1
    note = f"流式转换 {count} 条" + (f"，跳过 {skipped} 条" if skipped else "")
    return count, note


def _read_rows_mem(path: str) -> list:
    """非 jsonl 的内存读取：json 数组/含数组对象 → list[dict]；其它按行 → [{'text': line}]。"""
    import json as _json
    low = path.lower()
    if low.endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            data = _json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for v in data.values():
                if isinstance(v, list):
                    return v
        return []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return [{"text": ln.rstrip("\n")} for ln in f if ln.strip()]


def convert(rows: list, ds_type: str | None, rules: list | None = None) -> tuple[list, str]:
    """把业务原始 rows 转成 alpaca 样本列表。

    rules 为「该数据集类型的规则」（已由调用方按类型关联筛出）；传 None 时回退内置
    DEFAULT_RULES 按类型子串选规则（离线/无库场景）。返回 (samples, note)。
    """
    if not rows or not isinstance(rows[0], dict):
        return [], "数据为空或非对象数组，无法转换"
    if rules is None:
        rules = select_default_rules(ds_type)
    else:
        rules = sorted([r for r in rules if r.get("enabled", True)], key=lambda r: r.get("priority", 100))
    return apply_rules(rows, rules, ds_type)
