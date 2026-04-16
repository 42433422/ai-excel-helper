"""
用户输入智能解析模块：解析用户自然语言中的客户名称、产品型号等信息。
处理混合输入如"七彩乐园9803" -> 客户名"七彩乐园" + 产品编号"9803"

销售合同类长句优先走 ``sales_contract_intent_bridge``（单次结构化 LLM + 主数据对齐），
失败时降级规则 ``_rule_based_extraction``。
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)
_MODEL_TOKEN_PATTERN = r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*"


def _load_customers_set() -> set[str]:
    """加载客户名称集合"""
    try:
        try:
            from backend.routers.xcagi_compat import _load_customers_rows
        except ImportError:
            from routers.xcagi_compat import _load_customers_rows

        customers = _load_customers_rows()
        result = set()
        for c in customers:
            name = (c.get("customer_name") or c.get("name") or c.get("unit_name") or "").strip()
            if name:
                result.add(name)
        return result
    except Exception as e:
        logger.warning("failed to load customers: %s", e)
        return set()


def _load_products_set() -> set[str]:
    """加载产品型号集合"""
    try:
        try:
            from backend.routers.xcagi_compat import _load_products_all_for_export
        except ImportError:
            from routers.xcagi_compat import _load_products_all_for_export

        products = _load_products_all_for_export(keyword=None, unit=None)
        result = set()
        for p in products:
            model = (p.get("model_number") or "").strip()
            if model:
                result.add(model)
        return result
    except Exception as e:
        logger.warning("failed to load products: %s", e)
        return set()


def _normalize_text(text: str) -> str:
    """标准化文本"""
    if not text:
        return ""
    return text.strip().lower().replace(" ", "").replace("　", "")


def _chinese_to_number(text: str) -> int | None:
    """将中文数字转换为整数，支持“十二”“三十”“一百二十三”等复合写法。"""
    chinese_map = {
        "零": 0,
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
    unit_map = {"十": 10, "百": 100, "千": 1000}
    if not text:
        return None
    text = text.strip()
    try:
        return int(text)
    except ValueError:
        pass

    if text in chinese_map:
        return chinese_map[text]
    if text in unit_map:
        return unit_map[text]
    if not re.fullmatch(r"[零一二两三四五六七八九十百千]+", text):
        return None

    total = 0
    current = 0
    for ch in text:
        if ch in chinese_map:
            current = chinese_map[ch]
            continue
        if ch in unit_map:
            unit = unit_map[ch]
            if current == 0:
                current = 1
            total += current * unit
            current = 0
            continue
        return None

    return total + current


class UserInputParser:
    """
    智能解析用户输入中的客户名称、产品型号、数量等信息。
    """

    def __init__(self) -> None:
        self._customers: set[str] | None = None
        self._products: set[str] | None = None

    def _ensure_data(self) -> None:
        """惰性加载客户和产品数据"""
        if self._customers is None:
            self._customers = _load_customers_set()
        if self._products is None:
            self._products = _load_products_set()

    def _try_parse_combined(self, text: str) -> dict[str, Any] | None:
        """
        尝试解析混合输入如"七彩乐园9803"或"客户名产品编号"。
        返回 {"customer_name": xxx, "product_number": xxx} 或 None
        """
        self._ensure_data()

        text_norm = _normalize_text(text)
        if not text_norm:
            return None

        customers = self._customers or set()
        products = self._products or set()

        best_match = None
        best_score = 0

        for cust in customers:
            cust_norm = _normalize_text(cust)
            if not cust_norm:
                continue

            if text_norm.startswith(cust_norm):
                remaining = text_norm[len(cust_norm) :]
                for prod in products:
                    prod_norm = _normalize_text(prod)
                    if prod_norm and (
                        remaining == prod_norm
                        or prod_norm.startswith(remaining)
                        or remaining.startswith(prod_norm)
                    ):
                        score = len(cust_norm) + len(prod_norm)
                        if score > best_score:
                            best_score = score
                            best_match = {"customer_name": cust, "product_number": prod}

            elif cust_norm in text_norm:
                remaining_parts = [p for p in text_norm.split(cust_norm) if p]
                for remaining in remaining_parts:
                    for prod in products:
                        prod_norm = _normalize_text(prod)
                        if prod_norm == remaining or prod_norm in remaining or remaining in prod_norm:
                            score = len(cust_norm) + len(prod_norm)
                            if score > best_score:
                                best_score = score
                                best_match = {"customer_name": cust, "product_number": prod}

        return best_match

    def parse_user_input(self, text: str) -> dict[str, Any]:
        """
        解析用户输入，返回结构化信息。

        Returns:
            {
                "customer_name": str | None,
                "product_numbers": list[str],
                "product_name": str | None,
                "quantity": int | None,
                "original": str,
                "parsed": bool,
            }
        """
        self._ensure_data()

        text_stripped = text.strip()
        if not text_stripped:
            return {
                "customer_name": None,
                "product_numbers": [],
                "product_name": None,
                "quantity": None,
                "original": text,
                "parsed": False,
            }

        customers = self._customers or set()
        products = self._products or set()

        result = {
            "customer_name": None,
            "product_numbers": [],
            "product_name": None,
            "quantity": None,
            "original": text_stripped,
            "parsed": False,
        }

        combined = self._try_parse_combined(text_stripped)
        if combined:
            result["customer_name"] = combined["customer_name"]
            result["product_numbers"] = [combined["product_number"]]
            result["parsed"] = True
            return result

        for cust in customers:
            if _normalize_text(cust) == _normalize_text(text_stripped):
                result["customer_name"] = cust
                result["parsed"] = True
                return result

        for prod in products:
            if _normalize_text(prod) == _normalize_text(text_stripped):
                result["product_numbers"] = [prod]
                result["parsed"] = True
                return result

        numbers_match = re.findall(r"\d+", text_stripped)
        if numbers_match:
            for num in numbers_match:
                for prod in products:
                    if prod == num or _normalize_text(prod) == _normalize_text(num):
                        result["product_numbers"] = [prod]
                        result["parsed"] = True
                        break

        return result


_parser: UserInputParser | None = None


def get_parser() -> UserInputParser:
    """获取全局解析器实例"""
    global _parser
    if _parser is None:
        _parser = UserInputParser()
    return _parser


def parse_user_input(text: str) -> dict[str, Any]:
    """
    快捷函数：解析用户输入中的客户名、产品编号等信息。

    Example:
        result = parse_user_input("七彩乐园9803")
        # result = {"customer_name": "七彩乐园", "product_numbers": ["9803"], ...}

        result = parse_user_input("帮我打印销售合同客户是深圳市百木鼎家具有限公司，编号3721要三桶")
        # 返回解析出的客户名和产品编号
    """
    parser = get_parser()
    return parser.parse_user_input(text)


def _try_bridge_extraction(user_message: str) -> dict[str, Any] | None:
    """销售合同：单次 LLM + 主数据对齐（与 Planner/Orchestrator 同源）。"""
    try:
        from backend.sales_contract_intent_bridge import (
            extract_sales_contract_draft,
            message_suggests_sales_contract,
            resolve_draft_to_extract_structured_dict,
        )

        if not message_suggests_sales_contract(user_message):
            return None
        draft = extract_sales_contract_draft(user_message)
        if not draft:
            return None
        out = resolve_draft_to_extract_structured_dict(draft, raw_message=user_message)
        if out is None:
            # 草稿可能已由 LLM 产出；失败常在 ``resolve_draft_to_tool_slots`` 主数据对齐
            logger.info(
                "[user_input_parser] sales_contract bridge: draft ok but resolve returned no usable rows "
                "(customer/product match vs DB)"
            )
        return out
    except Exception as e:
        logger.debug("[user_input_parser] bridge extract skipped: %s", e)
        return None


def _try_llm_extraction(user_message: str) -> dict[str, Any] | None:
    """
    兼容旧测试对 ``_try_llm_extraction`` 的 monkeypatch；逻辑即 bridge 抽取。
    测试若将其置为 ``lambda _: None`` 则跳过 LLM，仅走规则降级。
    """
    return _try_bridge_extraction(user_message)


def extract_structured_info(user_message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    从用户消息中提取结构化信息（客户名、产品型号、数量等）。

    优先 ``_try_llm_extraction``（单次 LLM + 主数据对齐）；失败时：
    - **口语化销售合同长单**（须结构化思考）：不再用正则规则兜底，避免误拆型号；
    - 其余情况才 ``_rule_based_extraction``。
    """
    result = {
        "customer_name": None,
        "products": [],
        "quantities": {},
        "raw_message": user_message,
    }

    if not user_message:
        return result

    extracted = _try_llm_extraction(user_message)
    if extracted:
        result.update(extracted)
        logger.info("[user_input_parser] bridge/LLM 提取成功")
        return result

    try:
        from backend.sales_contract_intent_bridge import (
            message_suggests_sales_contract,
            sales_contract_utterance_requires_structured_llm,
        )

        if message_suggests_sales_contract(user_message) and sales_contract_utterance_requires_structured_llm(
            user_message
        ):
            logger.info(
                "[user_input_parser] 销售合同口语长单 bridge 无完整结果，跳过规则降级 "
                "（缺 API Key / LLM 未产出草稿 / 或草稿未能对齐主数据）"
            )
            return result
    except Exception:
        pass

    logger.info("[user_input_parser] bridge 不可用或未命中，降级规则匹配")
    return _rule_based_extraction(result, user_message)


def _rule_based_extraction(result: dict[str, Any], user_message: str) -> dict[str, Any]:
    """
    基于规则的产品和数量提取（降级方案）
    """
    customers = _load_customers_set()
    products = _load_products_set()

    for cust in customers:
        if cust in user_message or _normalize_text(cust) in _normalize_text(user_message):
            result["customer_name"] = cust
            break

    quantity_expr = r"(\d+|[零一二三四五六七八九十百千两]+)"

    patterns: list[tuple[str, int, int]] = [
        (rf"编号\s*({_MODEL_TOKEN_PATTERN})\s*(?:[要x×]\s*)?{quantity_expr}\s*桶", 1, 2),
        (rf"(?:需要|要)\s*{quantity_expr}\s*桶\s*[，,]?\s*({_MODEL_TOKEN_PATTERN})", 2, 1),
        (rf"{quantity_expr}\s*桶\s*[，,]?\s*({_MODEL_TOKEN_PATTERN})", 2, 1),
        (rf"({_MODEL_TOKEN_PATTERN})\s*{quantity_expr}\s*桶", 1, 2),
    ]

    def parse_qty(s: str) -> int:
        """解析数量，支持阿拉伯数字与复合中文数字。"""
        s = s.strip()
        try:
            return int(s)
        except ValueError:
            parsed = _chinese_to_number(s)
            return parsed if parsed is not None else 1

    found_products: set[str] = set()

    for pattern, model_group, qty_group in patterns:
        for match in re.finditer(pattern, user_message):
            model = match.group(model_group).strip()
            qty_str = match.group(qty_group)

            qty = parse_qty(qty_str)

            for prod in products:
                if _normalize_text(prod) == _normalize_text(model):
                    found_products.add(prod)
                    result["quantities"][prod] = qty
                    break

    for prod in products:
        prod_norm = _normalize_text(prod)
        if prod_norm and prod_norm in _normalize_text(user_message):
            if prod not in found_products:
                found_products.add(prod)
                if prod not in result["quantities"]:
                    result["quantities"][prod] = 1

    quantity_pattern = rf"({_MODEL_TOKEN_PATTERN})\s*[要x×]\s*{quantity_expr}\s*桶"
    for match in re.finditer(quantity_pattern, user_message):
        model = match.group(1).strip()
        qty = parse_qty(match.group(2))
        for prod in products:
            if _normalize_text(prod) == _normalize_text(model):
                found_products.add(prod)
                result["quantities"][prod] = qty
                break

    for match in re.finditer(rf"({_MODEL_TOKEN_PATTERN})\s*[x×]\s*(\d+)", user_message):
        model = match.group(1).strip()
        qty = int(match.group(2))
        for prod in products:
            if _normalize_text(prod) == _normalize_text(model):
                found_products.add(prod)
                result["quantities"][prod] = qty
                break

    result["products"] = list(found_products)

    return result
