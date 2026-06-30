"""数据脱敏引擎：把规则真实作用到样本内容上（数据驱动）。

两类掩码：
- 模式型(idcard/phone/bankcard/email)：用「规则自带正则 + 替换串」就地扫描所有字符串值/文本行替换，
  不依赖字段名（对结构化字段值和自由文本都生效）。规则未配正则时回退内置默认（见 BUILTIN_PATTERNS）——
  即正则与替换串都已落库、可在「数据集脱敏处理」页查看与编辑。
- 字段型(name/custom)：按规则 field 名匹配字典的键再掩码（name 留姓；custom 用 pattern 正则把命中处
  替换为 replacement，默认 ***；无 pattern 则整值替换）。

纯函数 + 数据驱动，便于单测。返回 (脱敏后数据, 命中次数)。
"""
import re

# 模式型内置默认 {maskType: (正则, 替换串)}。规则未自定义 pattern/replacement 时回退到此；均可被规则覆盖。
# 替换串为 re.sub 模板，支持 \1 \2 反向引用。
BUILTIN_PATTERNS = {
    "idcard":   (r"(?<!\d)(\d{6})\d{8}(\d{3}[\dXx])(?!\d)", r"\1********\2"),
    "phone":    (r"(?<!\d)(1[3-9]\d)\d{4}(\d{4})(?!\d)",     r"\1****\2"),
    "bankcard": (r"(?<!\d)\d{8,15}(\d{4})(?!\d)",            r"**** **** **** \1"),
    "email":    (r"([A-Za-z0-9._%+\-])[A-Za-z0-9._%+\-]*(@[A-Za-z0-9.\-]+)", r"\1***\2"),
}
# 模式型应用顺序：idcard 先于 bankcard，避免 18 位身份证被当卡号重复命中。
_PATTERN_ORDER = {"idcard": 0, "phone": 1, "bankcard": 2, "email": 3}

# 字段型掩码的键别名（忽略大小写、子串匹配）
_NAME_KEYS = ("姓名", "name", "人员", "嫌疑人", "当事人")


def _resolve_pattern(rule: dict):
    """取规则的(正则, 替换串)：优先规则自带，缺省回退内置默认；无可用正则返回 None。"""
    mt = rule.get("maskType")
    pat = (rule.get("pattern") or "").strip()
    rep = rule.get("replacement")
    default = BUILTIN_PATTERNS.get(mt)
    if not pat:
        if not default:
            return None
        pat, drep = default
        if rep is None or rep == "":
            rep = drep
    elif rep is None or rep == "":
        rep = default[1] if default else "***"
    return pat, rep


def _pattern_rules(rules: list) -> list:
    """模式型规则解析为 [(正则, 替换串)]，按既定顺序排序（idcard 先于 bankcard）。"""
    items = []
    for r in rules:
        if r.get("maskType") in _PATTERN_ORDER:
            resolved = _resolve_pattern(r)
            if resolved:
                items.append((_PATTERN_ORDER[r["maskType"]], resolved[0], resolved[1]))
    items.sort(key=lambda x: x[0])
    return [(pat, rep) for _o, pat, rep in items]


def mask_text(s: str, pattern_rules: list) -> str:
    """对一段文本依次套用模式型规则的(正则, 替换串)。非法正则跳过。"""
    for pat, rep in pattern_rules:
        try:
            s = re.sub(pat, rep, s)
        except re.error:
            continue
    return s


def _mask_name(v: str) -> str:
    v = str(v)
    return (v[0] + "*" * (len(v) - 1)) if len(v) > 1 else v


def _field_rules(rules: list) -> list:
    """字段型规则（name/custom），保留 field / pattern / replacement。"""
    return [r for r in rules if r.get("maskType") in ("name", "custom")]


def apply(data, rules: list):
    """对 data（list[dict] 或 list[str]）应用脱敏规则，返回 (脱敏后, 命中次数)。"""
    enabled = [r for r in rules if r.get("enabled", True)]
    pattern_rules = _pattern_rules(enabled)
    field_rules = _field_rules(enabled)
    hits = 0
    out = []
    for row in data:
        if isinstance(row, dict):
            new = {}
            for k, v in row.items():
                if isinstance(v, str):
                    masked = mask_text(v, pattern_rules)
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
            masked = mask_text(row, pattern_rules)
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
    rep = rule.get("replacement") or "***"
    if pat:
        try:
            return re.sub(pat, rep, value)
        except re.error:
            return value
    return rep if value else value
