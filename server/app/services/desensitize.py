"""数据脱敏引擎：把规则真实作用到样本内容上（不再是标志位）。

两类掩码：
- 模式型(idcard/phone/bankcard/email)：内置正则，扫所有字符串值/文本行就地替换，
  不依赖字段名（对结构化字段值和自由文本都生效）；
- 字段型(name/custom)：按规则 field 名匹配字典的键再掩码（name 留姓；custom 用 pattern
  正则替换，无 pattern 则整值替换为 ***）。

纯函数 + 数据驱动，便于单测。返回 (脱敏后数据, 命中次数)。
"""
import re

_RE_IDCARD = re.compile(r"(?<!\d)(\d{6})\d{8}(\d{3}[\dXx])(?!\d)")
_RE_PHONE = re.compile(r"(?<!\d)(1[3-9]\d)\d{4}(\d{4})(?!\d)")
_RE_BANKCARD = re.compile(r"(?<!\d)\d{12,19}(?!\d)")
_RE_EMAIL = re.compile(r"([A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]*(@[A-Za-z0-9.\-]+)")

# 字段型掩码的键别名（忽略大小写、子串匹配）
_NAME_KEYS = ("姓名", "name", "人员", "嫌疑人", "当事人")


def _mask_bankcard_one(m: re.Match) -> str:
    s = m.group(0)
    return "*" * (len(s) - 4) + s[-4:]


def mask_text(s: str, types: set) -> str:
    """对一段文本按启用的「模式型」掩码逐个应用。idcard 先于 bankcard，避免重复命中。"""
    if "idcard" in types:
        s = _RE_IDCARD.sub(lambda m: m.group(1) + "********" + m.group(2), s)
    if "phone" in types:
        s = _RE_PHONE.sub(lambda m: m.group(1) + "****" + m.group(2), s)
    if "bankcard" in types:
        s = _RE_BANKCARD.sub(_mask_bankcard_one, s)
    if "email" in types:
        s = _RE_EMAIL.sub(lambda m: m.group(1) + "***" + m.group(2), s)
    return s


def _mask_name(v: str) -> str:
    v = str(v)
    return (v[0] + "*" * (len(v) - 1)) if len(v) > 1 else v


def _field_rules(rules: list) -> list:
    """字段型规则（name/custom），保留 field 与 pattern。"""
    return [r for r in rules if r.get("maskType") in ("name", "custom")]


def apply(data, rules: list):
    """对 data（list[dict] 或 list[str]）应用脱敏规则，返回 (脱敏后, 命中次数)。"""
    enabled = [r for r in rules if r.get("enabled", True)]
    pattern_types = {r["maskType"] for r in enabled if r.get("maskType") in ("idcard", "phone", "bankcard", "email")}
    field_rules = _field_rules(enabled)
    hits = 0
    out = []
    for row in data:
        if isinstance(row, dict):
            new = {}
            for k, v in row.items():
                if isinstance(v, str):
                    masked = mask_text(v, pattern_types)
                    # 字段型：键名命中规则 field 时再处理
                    for fr in field_rules:
                        if _key_hit(k, fr.get("field"), fr.get("maskType")):
                            masked = _apply_field(masked, fr)
                    if masked != v:
                        hits += 1
                    new[k] = masked
                else:
                    new[k] = v
            out.append(new)
        elif isinstance(row, str):
            masked = mask_text(row, pattern_types)
            if masked != row:
                hits += 1
            out.append(masked)
        else:
            out.append(row)
    return out, hits


def _key_hit(key: str, field: str, mask_type: str) -> bool:
    """字典键是否命中规则字段：字段名互为子串即命中；name 型再用姓名别名兜底。"""
    k = (key or "").lower()
    f = (field or "").lower()
    if f and (f in k or k in f):
        return True
    if mask_type == "name":
        return any(a.lower() in k for a in _NAME_KEYS)
    return False


def _apply_field(value: str, rule: dict) -> str:
    mt = rule.get("maskType")
    if mt == "name":
        return _mask_name(value)
    # custom
    pat = rule.get("pattern")
    if pat:
        try:
            return re.sub(pat, "***", value)
        except re.error:
            return value
    return "***" if value else value
