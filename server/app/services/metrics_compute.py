"""评估指标计算：对 (prompt, gold, pred) 三元组列表算真实指标。

文本层（任何文本输出通用）：字符/词级 micro 精确率·召回率·F1 + 完全匹配率。
结构层（NER/关系/事件）：尽力把输出解析成带类型的片段集合，算各类别 P/R/F1；
解析不出实体时各类别回退为「整体」一行（用文本层结果），不编造数据。
"""
import json
import re
from collections import Counter, defaultdict


# ---- 模型类型归一（中文 label / 英文 value → 指标页用的英文 key）----
def norm_model_type(s: str | None) -> str:
    t = (s or "").lower()
    if "ocr" in t:
        return "ocr"
    if "关系" in t or "relation" in t:
        return "relation"
    if "实体" in t or "ner" in t:
        return "ner"
    if "事件" in t or "event" in t:
        return "event"
    if "风险" in t or "risk" in t:
        return "risk"
    if "路径" in t or "轨迹" in t or "path" in t:
        return "path"
    return t or "ner"


def load_alpaca(path: str) -> list[dict]:
    """读 alpaca 训练文件（jsonl 或 json 数组），返回 {instruction,input,output} 列表。"""
    rows = []
    low = path.lower()
    with open(path, "r", encoding="utf-8") as f:
        if low.endswith(".jsonl"):
            for line in f:
                s = line.strip()
                if s:
                    try:
                        rows.append(json.loads(s))
                    except Exception:
                        pass
        else:
            data = json.load(f)
            if isinstance(data, list):
                rows = data
            elif isinstance(data, dict):
                for v in data.values():
                    if isinstance(v, list):
                        rows = v
                        break
    return [r for r in rows if isinstance(r, dict)]


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "")).strip().lower()


_TOK = re.compile(r"[0-9a-zA-Z]+|[一-鿿]")


def _tok(text: str) -> list[str]:
    """分词：连续英数为一词，中文逐字。供字符/词级 P/R/F1。"""
    return _TOK.findall((text or "").lower())


def _prf(tp: int, fp: int, fn: int):
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    f = 2 * p * r / (p + r) if (p + r) else 0.0
    return p, r, f


# ---- 结构化输出 → 带类型片段集合 ----
def _from_json(obj) -> set:
    ents = set()
    type_keys = ("type", "label", "entity_type", "类型", "标签")
    val_keys = ("text", "value", "mention", "name", "值", "实体", "内容")
    if isinstance(obj, list):
        for it in obj:
            if isinstance(it, dict):
                typ = next((str(it[k]) for k in type_keys if k in it), "")
                val = next((str(it[k]) for k in val_keys if k in it), "")
                if val:
                    ents.add((typ or "实体", val.strip()))
            elif isinstance(it, (list, tuple)) and len(it) >= 2:
                ents.add((str(it[1]).strip(), str(it[0]).strip()))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, list):
                for x in v:
                    ents.add((str(k), str(x).strip()))
            elif isinstance(v, str):
                ents.add((str(k), v.strip()))
    return {(t, x) for t, x in ents if x}


_VAL_TYPE = re.compile(r"([^\s,，/、]+)\s*/\s*([一-鿿A-Za-z_]+)")
_TYPE_VAL = re.compile(r"([一-鿿A-Za-z_]{1,12})\s*[:：]\s*([^,，;；\n\]\}]+)")


def _parse_entities(text: str) -> set:
    """尽力解析输出为 {(类型, 值)} 集合：先 JSON，再「值/类型」，再「类型: 值」。"""
    text = (text or "").strip()
    if not text:
        return set()
    for cand in (text, re.sub(r"^[^\[\{]*", "", text)):
        try:
            return _from_json(json.loads(cand)) or set()
        except Exception:
            continue
    ents = {(m.group(2).strip(), m.group(1).strip()) for m in _VAL_TYPE.finditer(text)}
    if ents:
        return ents
    return {(m.group(1).strip(), m.group(2).strip()) for m in _TYPE_VAL.finditer(text)}


def _err_type(gold: str, pred: str, f1: float) -> str:
    if not (pred or "").strip():
        return "漏识别"
    if f1 == 0:
        return "完全错误"
    if len(pred) > 2 * max(1, len(gold)):
        return "过度生成"
    return "部分错误"


def evaluate(preds: list[tuple], model_type: str, max_errors: int = 20) -> dict:
    """preds: [(prompt, gold, pred)]。返回 metrics/perClass/errors + 总体 P/R/F1。"""
    n = len(preds)
    tp = fp = fn = 0
    exact = 0
    per = defaultdict(lambda: [0, 0, 0])   # 类型 -> [tp,fp,fn]
    any_entities = False
    errors = []

    for prompt, gold, pred in preds:
        g, p = Counter(_tok(gold)), Counter(_tok(pred))
        inter = sum((g & p).values())
        s_tp, s_fp, s_fn = inter, sum(p.values()) - inter, sum(g.values()) - inter
        tp += s_tp; fp += s_fp; fn += s_fn
        _, _, s_f1 = _prf(s_tp, s_fp, s_fn)
        if _norm(pred) == _norm(gold):
            exact += 1
        else:
            errors.append((s_f1, _err_type(gold, pred, s_f1), prompt, gold, pred))

        ge, pe = _parse_entities(gold), _parse_entities(pred)
        if ge:
            any_entities = True
        gc, pc = Counter(ge), Counter(pe)
        for key in set(gc) | set(pc):
            t = key[0] or "实体"
            i = min(gc[key], pc[key])
            per[t][0] += i
            per[t][1] += max(0, pc[key] - i)
            per[t][2] += max(0, gc[key] - i)

    P, R, F1 = _prf(tp, fp, fn)
    metrics = [
        ("精确率", round(P * 100, 1), "%"),
        ("召回率", round(R * 100, 1), "%"),
        ("F1 值", round(F1 * 100, 1), "%"),
        ("完全匹配率", round(exact / n * 100, 1) if n else 0, "%"),
        ("评估样本数", n, "条"),
    ]

    if any_entities:
        per_class = []
        for t, (a, b, c) in sorted(per.items(), key=lambda x: -(x[1][0] + x[1][2])):
            p_, r_, f_ = _prf(a, b, c)
            per_class.append({"label": t, "precision": round(p_ * 100, 1),
                              "recall": round(r_ * 100, 1), "f1": round(f_ * 100, 1)})
        per_class = per_class[:12]
    else:
        per_class = [{"label": "整体", "precision": round(P * 100, 1),
                      "recall": round(R * 100, 1), "f1": round(F1 * 100, 1)}]

    errors.sort(key=lambda x: x[0])   # F1 升序：最差的在前
    err_out = [{"errorType": et, "content": (prompt or "")[:255],
                "expected": (gold or "")[:255], "actual": (pred or "")[:255]}
               for _f, et, prompt, gold, pred in errors[:max_errors]]

    return {"precision": round(P, 4), "recall": round(R, 4), "f1": round(F1, 4),
            "metrics": metrics, "perClass": per_class, "errors": err_out,
            "exactRate": round(exact / n, 4) if n else 0, "samples": n}
