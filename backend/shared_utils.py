"""
共享工具函数
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def find_matching_customer(input_name: str) -> Optional[str]:
    """从数据库查找最匹配的客户名称（模糊匹配）；支持 DATABASE_URL 指向的 PostgreSQL 或 SQLite。"""
    from backend.product_db_read import find_matching_customer_unified

    return find_matching_customer_unified(input_name)


def extract_customer_name(message: str) -> Optional[str]:
    """从用户消息中提取客户名称"""
    import re

    message = message.strip()
    if not message:
        return None

    # 「百木鼎家具有限公司」：从「有限公司/…公司」等后缀向左取连续汉字，避免 ``[\u4e00-\u9fa5]{2,40}`` 从句首贪婪吞整句
    _han = re.compile(r"[\u4e00-\u9fff]")
    _utterance_prefix = re.compile(
        r"^(?:请|麻烦|帮我|给我|我要|想|需要|打一下|打份|打|生成|开|做|弄|导出|下载|来一份|来)",
    )
    _biz_noise = ("销售合同", "价格表", "报价表", "送货单", "发货单")

    # 口语：「那个惠州市丰驰家居的那个销售合同」——店名夹在两个「那个」之间，未必含「有限公司」
    m_that = re.search(
        r"那个\s*([\u4e00-\u9fff]{4,28}?)\s*那个\s*(?:的\s*)?(?:销售)?合同",
        message,
    )
    if m_that:
        cand = m_that.group(1).strip().rstrip("的").strip()
        if len(cand) >= 4 and not any(n in cand for n in _biz_noise):
            return cand

    # 「XX市…家居/家具/公司」等口头店名（无「有限公司」后缀）
    m_city = re.search(
        r"([\u4e00-\u9fff]{2,4}市[\u4e00-\u9fff]{2,16}(?:家居|家具|家私|有限公司|股份有限公司|集团公司|公司|厂|店))",
        message,
    )
    if m_city:
        cand = m_city.group(1).strip()
        if 4 <= len(cand) <= 28 and not any(n in cand for n in _biz_noise):
            return cand

    for kw in ("有限公司", "股份有限公司", "集团公司"):
        for m in re.finditer(re.escape(kw), message):
            end = m.end()
            j = m.start()
            while j > 0 and (end - j) < 42 and _han.match(message[j - 1]):
                j -= 1
            cand = message[j:end].strip()
            for _ in range(12):
                m0 = _utterance_prefix.match(cand)
                if not m0:
                    break
                cand = cand[m0.end() :].lstrip(" ，,。；;").strip()
            if len(cand) < 6:
                continue
            if any(n in cand for n in _biz_noise):
                continue
            return cand
    for m in re.finditer(r"(?:公司|厂|店|单位)(?![\u4e00-\u9fff])", message):
        end = m.end()
        j = m.start()
        while j > 0 and (end - j) < 22 and _han.match(message[j - 1]):
            j -= 1
        cand = message[j:end].strip()
        if len(cand) < 4 or len(cand) > 24:
            continue
        if any(n in cand for n in _biz_noise):
            continue
        if _utterance_prefix.match(cand):
            continue
        return cand

    patterns = [
        r'客户名称 [是为是]*([^\s，,。]{4,20} 公司)',
    ]

    for pattern in patterns:
        match = re.search(pattern, message)
        if match:
            result = re.sub(r'^是', '', match.group(1)).strip()
            if result and len(result) >= 4 and ('公司' in result or '单位' in result or '客户' in result or '厂' in result or '店' in result):
                return result

    city_keywords = ['市', '县', '区']
    for keyword in city_keywords:
        start_idx = message.find(keyword)
        if start_idx != -1 and start_idx >= 1:
            city_start = start_idx - min(2, start_idx)
            city_name = message[city_start:start_idx + 1]
            if len(city_name) >= 2 and len(city_name) <= 4:
                rest = message[start_idx + 1:]
                company_end = rest.find('公司')
                if company_end != -1 and company_end >= 1 and company_end <= 10:
                    full_name = city_name + rest[:company_end + 2]
                    if len(full_name) >= 6 and len(full_name) <= 20:
                        return full_name

    matches = list(re.finditer(r'([\u4e00-\u9fa5]{2,15} 公司)', message))
    if matches:
        last = matches[-1].group(1)
        forbidden = ['打印', '生成', '创建', '销售', '价格', '帮我', '给我']
        for f in forbidden:
            if f in last:
                last = last.replace(f, '')
        while len(last) >= 4 and last[0] in '我你他要一下':
            last = last[1:]
        if len(last) >= 4:
            return last

    return None
