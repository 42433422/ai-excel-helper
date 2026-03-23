# -*- coding: utf-8 -*-
"""
中文数字解析工具

支持 0-99 的中文数字转换
"""

import re
from typing import Optional


def cn_to_number(cn: str) -> Optional[int]:
    """
    将中文数字转换为整数

    支持范围：零/〇 → 0 到 九十九 → 99

    规则：
    - 个位：零(0) 一(1) 二(2) 两(2) 三(3) 四(4) 五(5) 六(6) 七(7) 八(8) 九(9)
    - 十位：十(10) 十几(11-19) 几十(20/30/.../90) 几十几(21-99)

    Examples:
        零 → 0, 一 → 1, 十 → 10, 十一 → 11, 二十 → 20, 二十八 → 28, 九十九 → 99

    Args:
        cn: 中文数字字符串

    Returns:
        转换后的整数，解析失败返回 None
    """
    if not cn:
        return None

    cn = cn.strip()

    _CN_MAP = {
        '零': 0, '〇': 0,
        '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10,
    }

    # 精确匹配个位数
    if cn in _CN_MAP:
        return _CN_MAP[cn]

    # 匹配 "十几" 模式 (11-19)
    if len(cn) == 2 and cn[1] == '十':
        if cn[0] in _CN_MAP:
            return 10 + _CN_MAP[cn[0]]  # 十一 → 1*10 + 1 = 11

    # 匹配 "几十" 模式 (20/30/.../90)
    if len(cn) == 2 and cn[0] in '一两二三四五六七八九' and cn[1] == '十':
        if cn[0] in _CN_MAP:
            return _CN_MAP[cn[0]] * 10  # 二十 → 2*10 = 20

    # 匹配 "几十几" 模式 (21-99，但不含10-19)
    if len(cn) == 3 and cn[1] == '十' and cn[2] in _CN_MAP:
        if cn[0] in _CN_MAP:
            return _CN_MAP[cn[0]] * 10 + _CN_MAP[cn[2]]

    return None


def extract_number_from_text(text: str) -> Optional[int]:
    """
    从文本中提取中文或阿拉伯数字

    优先提取阿拉伯数字，如果不存在则尝试提取中文数字

    Args:
        text: 原始文本

    Returns:
        提取到的数字，或 None
    """
    if not text:
        return None

    # 先尝试阿拉伯数字
    arabic_match = re.search(r'(\d+)', text)
    if arabic_match:
        try:
            return int(arabic_match.group(1))
        except ValueError:
            pass

    # 尝试中文数字（向前看最多3个字符）
    cn_match = re.search(r'[零〇一二两三四五六七八九十]{1,3}', text)
    if cn_match:
        return cn_to_number(cn_match.group(0))

    return None


def parse_quantity_with_unit(text: str, unit: str = '桶') -> Optional[int]:
    """
    从文本中解析 "数字+单位" 形式的数量

    Args:
        text: 原始文本
        unit: 单位名称，默认 '桶'

    Returns:
        解析到的数量，或 None
    """
    if not text:
        return None

    # 构建正则：可选的"多少"/"共"等前缀 + 数字(中文或阿拉伯) + 单位
    pattern = rf'(?:共|要|来|拿|多少|)?\s*(\d+|[零〇一二两三四五六七八九十]{{1,3}})\s*{unit}'
    match = re.search(pattern, text)
    if match:
        num_str = match.group(1)
        if re.match(r'^\d+$', num_str):
            return int(num_str)
        return cn_to_number(num_str)

    return None


# 保持向后兼容
_cn_number = cn_to_number
