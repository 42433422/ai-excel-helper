from __future__ import annotations

import re

CHINESE_DIGIT_MAP = {
    "零": "0",
    "〇": "0",
    "一": "1",
    "二": "2",
    "三": "3",
    "四": "4",
    "五": "5",
    "六": "6",
    "七": "7",
    "八": "8",
    "九": "9",
    "两": "2",
}

ASR_MODEL_SEGMENT_MAP = {
    "酒吧": "98",
}

_CN_NUMBER_MAP = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


def parse_cn_number(token: str):
    t = (token or "").strip()
    if not t:
        return None
    if re.fullmatch(r"\d+(?:\.\d+)?", t):
        return float(t) if "." in t else int(t)

    m = _CN_NUMBER_MAP
    if t in m:
        return m[t]
    if t == "十":
        return 10
    if re.fullmatch(r"[一二两三四五六七八九]十", t):
        return m[t[0]] * 10
    if re.fullmatch(r"十[一二三四五六七八九]", t):
        return 10 + m[t[1]]
    if re.fullmatch(r"[一二两三四五六七八九]十[一二三四五六七八九]", t):
        return m[t[0]] * 10 + m[t[2]]
    return None


def cleanup_unit_name(raw: str) -> str:
    s = (raw or "").strip()
    s = re.sub(r"^(哎|嗯|啊|呃)[，,\s]*", "", s)
    s = re.sub(r"^(帮我|给我|请)?\s*打印(一下)?", "", s)
    s = re.sub(r"^(把|给)?", "", s)
    s = re.sub(
        r"^(再加|还要|继续加|再补|加上|增加|加|减少|减去|减|删掉|删除|去掉|移除|改成|改为|改)\s*",
        "",
        s,
    )
    s = s.replace("发货单", "").replace("送货单", "").replace("出货单", "")
    for token in [
        "打印一下",
        "打印",
        "给我",
        "帮我",
        "一下",
        "哎",
        "嗯",
        "啊",
        "呃",
        "桶",
        "要",
        "来",
        "拿",
        "再加",
        "还要",
        "继续加",
        "再补",
        "减少",
        "减去",
        "减",
        "删掉",
        "删除",
        "去掉",
        "移除",
        "改成",
        "改为",
    ]:
        s = s.replace(token, "")
    s = re.sub(r"[0-9A-Za-z-]{3,16}", "", s)
    s = re.sub(r"\s+", "", s)
    s = s.rstrip("的").strip()
    return s


def build_missing_prompt(unit_name=None, model_number=None, tin_spec=None, quantity_tins=None):
    missing = []
    if not unit_name:
        missing.append("单位")
    if not quantity_tins:
        missing.append("桶数")
    if not model_number:
        missing.append("编号/型号")
    if not tin_spec:
        missing.append("规格")
    if not missing:
        return None
    recognized = []
    if unit_name:
        recognized.append(f"单位 {unit_name}")
    if model_number:
        recognized.append(f"编号 {model_number}")
    if tin_spec:
        recognized.append(f"规格 {tin_spec}")
    recognized_text = ("（已识别：" + "，".join(recognized) + "）") if recognized else ""
    if missing == ["桶数"]:
        return f"还缺少桶数，请告诉我需要多少桶？{recognized_text}"
    if missing == ["单位"]:
        return f"还缺少单位名称，请补充购买单位。{recognized_text}"
    if missing == ["规格"]:
        return f"还缺少规格，请补充规格数值。{recognized_text}"
    if missing == ["编号/型号"]:
        return f"还缺少编号/型号，请补充。{recognized_text}"
    return f"还缺少{'、'.join(missing)}，请补充。{recognized_text}"


def normalize_trailing_unit_name(name: str) -> str:
    return (name or "").strip().rstrip("的").strip()


def normalize_chinese_digits(token: str) -> str:
    token = (token or "").strip()
    if not token:
        return ""

    if re.fullmatch(r"\d+(?:\.\d+)?", token):
        return token

    if all(ch in CHINESE_DIGIT_MAP for ch in token):
        return "".join(CHINESE_DIGIT_MAP[ch] for ch in token)

    digits = []
    for ch in token:
        if ch in CHINESE_DIGIT_MAP:
            digits.append(CHINESE_DIGIT_MAP[ch])
    return "".join(digits)


def normalize_quantity_token(quantity_token: str):
    quantity_token = (quantity_token or "").strip()
    if not quantity_token:
        return None
    if re.fullmatch(r"\d+", quantity_token):
        return int(quantity_token)
    digits = normalize_chinese_digits(quantity_token)
    if digits.isdigit():
        return int(digits)
    return None


def normalize_model_number_token(model_token: str) -> str:
    token = (model_token or "").strip()
    if not token:
        return ""

    compact = re.sub(r"\s+", "", token)
    if re.fullmatch(r"[0-9A-Za-z-]+", compact):
        return compact.upper()

    for k, v in ASR_MODEL_SEGMENT_MAP.items():
        if k in token:
            token = token.replace(k, v)

    out: list[str] = []
    for ch in token:
        if ch.isdigit():
            out.append(ch)
        elif ch in CHINESE_DIGIT_MAP:
            out.append(CHINESE_DIGIT_MAP[ch])
        elif ch.isalpha():
            out.append(ch.upper())
        elif ch == "-":
            out.append(ch)
    return "".join(out)
