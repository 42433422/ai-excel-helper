"""
合同产品校验模块：在生成销售合同前校验产品型号和客户名称是否在数据库中存在。
解决"生成数据库没有的单位的产品合同"问题。
"""

from __future__ import annotations

from datetime import date, datetime, time
import logging
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)


def _to_json_safe(value: Any) -> Any:
    """递归转换为 JSON 友好类型，避免 Decimal/datetime 进入 HTTP 响应。"""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _to_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_json_safe(v) for v in value]
    return str(value)


def _load_all_products() -> dict[str, dict[str, Any]]:
    """从数据库加载所有产品，按型号建立索引"""
    try:
        from backend.routers.xcagi_compat import _load_products_all_for_export
        products = _load_products_all_for_export(keyword=None, unit=None)
        index = {}
        for p in products:
            model = (p.get("model_number") or "").strip()
            if model:
                # 使用统一的清理逻辑
                model_clean = _normalize_for_comparison(model)
                if model_clean:
                    index[model_clean] = p
            name = (p.get("name") or "").strip()
            if name:
                name_clean = _normalize_for_comparison(name)
                if name_clean:
                    index[name_clean] = p
        return index
    except Exception as e:
        logger.warning("failed to load products for validation: %s", e)
        return {}


def _load_all_customers() -> dict[str, dict[str, Any]]:
    """从数据库加载所有客户/购买单位"""
    try:
        from backend.routers.xcagi_compat import _load_customers_rows
        customers = _load_customers_rows()
        index = {}
        for c in customers:
            name = (c.get("customer_name") or c.get("name") or c.get("unit_name") or "").strip()
            if name:
                index[name.lower()] = c
        return index
    except Exception as e:
        logger.warning("failed to load customers for validation: %s", e)
        return {}


def _normalize_for_comparison(text: str) -> str:
    """标准化文本用于比较：去除所有空白字符、转小写"""
    if not text:
        return ""
    # 使用 split() 去除所有空白字符（空格、制表符、换行等）
    return "".join(text.split()).lower()


def _normalize_model_for_fuzzy_match(text: str) -> str:
    """型号模糊匹配标准化：移除常见分隔符（如 - _ 空白）并转小写。"""
    if not text:
        return ""
    t = _normalize_for_comparison(text)
    return t.replace("-", "").replace("_", "")


class ContractValidator:
    """
    销售合同产品校验器。
    校验客户名称和产品型号是否在数据库中存在，并提供修正建议。
    """

    def __init__(self) -> None:
        self._products_index: dict[str, dict[str, Any]] | None = None
        self._customers_index: dict[str, dict[str, Any]] | None = None

    def _ensure_indices(self) -> None:
        """惰性加载数据库索引"""
        if self._products_index is None:
            self._products_index = _load_all_products()
        if self._customers_index is None:
            self._customers_index = _load_all_customers()

    def validate_customer(self, customer_name: str) -> dict[str, Any]:
        """
        校验客户名称是否存在。

        Returns:
            {
                "valid": bool,
                "original": str,
                "normalized": str,
                "matched_customer": dict | None,
                "suggestion": str | None,
                "message": str
            }
        """
        self._ensure_indices()

        if not customer_name or not customer_name.strip():
            return {
                "valid": False,
                "original": customer_name or "",
                "normalized": "",
                "matched_customer": None,
                "suggestion": None,
                "message": "客户名称不能为空",
            }

        original = customer_name.strip()
        normalized = _normalize_for_comparison(original)

        if not self._customers_index:
            return {
                "valid": False,
                "original": original,
                "normalized": normalized,
                "matched_customer": None,
                "suggestion": None,
                "message": "无法连接客户数据库进行校验",
            }

        if normalized in self._customers_index:
            return {
                "valid": True,
                "original": original,
                "normalized": normalized,
                "matched_customer": _to_json_safe(self._customers_index[normalized]),
                "suggestion": None,
                "message": f"客户「{original}」校验通过",
            }

        suggestions = []
        for db_name in self._customers_index:
            db_name_clean = db_name.replace(" ", "").replace("　", "")
            if normalized in db_name_clean or db_name_clean in normalized:
                suggestions.append(self._customers_index[db_name].get("customer_name") or db_name)

        suggestion = suggestions[0] if suggestions else None

        if suggestion:
            return {
                "valid": False,
                "original": original,
                "normalized": normalized,
                "matched_customer": None,
                "suggestion": suggestion,
                "message": f"客户「{original}」不存在，是否指「{suggestion}」？",
            }

        # 与 ``run_sales_contract_generation`` / ``/api/customers/match`` 同源：整句先抽取再 purchase_units 模糊匹配
        try:
            from backend.shared_utils import extract_customer_name, find_matching_customer

            resolved = find_matching_customer(original)
            if not resolved:
                ex = extract_customer_name(original)
                if ex:
                    resolved = find_matching_customer(ex)
            if resolved:
                nk = _normalize_for_comparison(resolved)
                row = self._customers_index.get(nk)
                if row is None:
                    for _k, r in self._customers_index.items():
                        nm = (r.get("customer_name") or r.get("name") or r.get("unit_name") or "").strip()
                        if nm == resolved or _normalize_for_comparison(nm) == nk:
                            row = r
                            break
                if row is not None:
                    return {
                        "valid": True,
                        "original": original,
                        "normalized": nk,
                        "matched_customer": _to_json_safe(row),
                        "suggestion": None,
                        "message": f"客户「{original}」已对齐为「{resolved}」并校验通过",
                    }
        except Exception as e:
            logger.warning("validate_customer fallback match failed: %s", e)

        return {
            "valid": False,
            "original": original,
            "normalized": normalized,
            "matched_customer": None,
            "suggestion": None,
            "message": f"客户「{original}」在数据库中不存在",
        }

    def validate_product(self, model_number: str, product_name: str | None = None) -> dict[str, Any]:
        """
        校验产品型号是否存在。

        Args:
            model_number: 产品型号
            product_name: 可选的产品名称（用于更精确的匹配）

        Returns:
            {
                "valid": bool,
                "original_model": str,
                "matched_product": dict | None,
                "suggestions": list[str],
                "message": str
            }
        """
        self._ensure_indices()

        original_model = (model_number or "").strip()
        if not original_model:
            return {
                "valid": False,
                "original_model": original_model,
                "matched_product": None,
                "suggestions": [],
                "message": "产品型号不能为空",
            }

        if not self._products_index:
            return {
                "valid": False,
                "original_model": original_model,
                "matched_product": None,
                "suggestions": [],
                "message": "无法连接产品数据库进行校验",
            }

        normalized = _normalize_for_comparison(original_model)

        if normalized in self._products_index:
            return {
                "valid": True,
                "original_model": original_model,
                "matched_product": _to_json_safe(self._products_index[normalized]),
                "suggestions": [],
                "message": f"产品型号「{original_model}」校验通过",
            }

        # 符号容错：如输入 7726，可在唯一候选下匹配到 7726-50f。
        fuzzy_matches: list[dict[str, Any]] = []
        normalized_base = _normalize_model_for_fuzzy_match(original_model)
        if normalized_base:
            seen_models: set[str] = set()
            for product in self._products_index.values():
                db_model = (product.get("model_number") or "").strip()
                if not db_model:
                    continue
                db_model_norm = _normalize_for_comparison(db_model)
                db_model_base = _normalize_model_for_fuzzy_match(db_model)
                if db_model in seen_models:
                    continue
                seen_models.add(db_model)

                if (
                    db_model_base == normalized_base
                    or db_model_norm.startswith(f"{normalized}-")
                    or normalized.startswith(f"{db_model_norm}-")
                ):
                    fuzzy_matches.append(product)

        if len(fuzzy_matches) == 1:
            matched = fuzzy_matches[0]
            matched_model = (matched.get("model_number") or "").strip()
            return {
                "valid": True,
                "original_model": original_model,
                "matched_product": _to_json_safe(matched),
                "suggestions": [],
                "message": (
                    f"产品型号「{original_model}」自动匹配为「{matched_model}」并校验通过"
                ),
            }

        suggestions = []
        matched_products = []

        for db_key, product in self._products_index.items():
            db_model = (product.get("model_number") or "").strip()
            db_name = (product.get("name") or "").strip()

            db_key_clean = db_key.replace(" ", "").replace("　", "")
            db_model_clean = _normalize_for_comparison(db_model)

            if normalized in db_model_clean or db_model_clean in normalized:
                suggestions.append(db_model)
                matched_products.append(product)
            elif db_name and (normalized in _normalize_for_comparison(db_name) or _normalize_for_comparison(db_name) in normalized):
                suggestions.append(f"{db_model} ({db_name})" if db_model else db_name)
                matched_products.append(product)

        if fuzzy_matches:
            for p in fuzzy_matches:
                m = (p.get("model_number") or "").strip()
                if m:
                    suggestions.append(m)
            suggestions = list(dict.fromkeys(suggestions))

        if suggestions:
            return {
                "valid": False,
                "original_model": original_model,
                "matched_product": None,
                "suggestions": suggestions[:5],
                "message": f"产品型号「{original_model}」不存在，是否指：{', '.join(suggestions[:3])}",
            }

        return {
            "valid": False,
            "original_model": original_model,
            "matched_product": None,
            "suggestions": [],
            "message": f"产品型号「{original_model}」在数据库中不存在",
        }

    def validate_contract(
        self,
        customer_name: str,
        products: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        校验完整合同数据。

        Args:
            customer_name: 客户名称
            products: 产品列表，每个产品包含 model_number 等字段

        Returns:
            {
                "valid": bool,
                "customer_result": dict,
                "products_result": list[dict],
                "invalid_products": list[dict],
                "valid_products": list[dict],
                "message": str
            }
        """
        customer_result = self.validate_customer(customer_name)

        products_result = []
        invalid_products = []
        valid_products = []

        for p in products:
            model = p.get("model_number") or ""
            name = p.get("name") or ""
            result = self.validate_product(model, name)

            if result["valid"]:
                validated_product = dict(result["matched_product"])
                validated_product["quantity"] = p.get("quantity", 1)
                validated_product["_original_input"] = model
                valid_products.append(validated_product)
            else:
                invalid_p = dict(p)
                invalid_p["_validation_result"] = result
                invalid_products.append(invalid_p)

            products_result.append(result)

        all_valid = customer_result["valid"] and len(invalid_products) == 0

        messages = []
        if not customer_result["valid"]:
            messages.append(f"客户名称：{customer_result['message']}")
        if invalid_products:
            for inv in invalid_products:
                vr = inv.get("_validation_result", {})
                messages.append(f"产品 {inv.get('model_number', '?')}: {vr.get('message', '校验失败')}")

        return {
            "valid": all_valid,
            "customer_result": customer_result,
            "products_result": products_result,
            "invalid_products": invalid_products,
            "valid_products": valid_products,
            "message": "\n".join(messages) if messages else "校验通过",
        }


_VALIDATOR: ContractValidator | None = None


def get_validator() -> ContractValidator:
    """获取全局校验器实例（惰性加载）"""
    global _VALIDATOR
    if _VALIDATOR is None:
        _VALIDATOR = ContractValidator()
    return _VALIDATOR


def validate_contract(customer_name: str, products: list[dict[str, Any]]) -> dict[str, Any]:
    """
    快捷函数：校验合同数据。

    Example:
        result = validate_contract("深圳市百木鼎家具有限公司", [
            {"model_number": "3721", "quantity": 3},
            {"model_number": "1870D", "quantity": 3},
        ])
        if not result["valid"]:
            print("校验失败:", result["message"])
            print("无效产品:", result["invalid_products"])
    """
    validator = get_validator()
    return validator.validate_contract(customer_name, products)


def augment_validate_contract_client_fields(result: dict[str, Any]) -> dict[str, Any]:
    """
    将 ``validate_contract`` 返回体展开为顶层字段，供 ``get_last_tool_result``、
    SSE ``done`` 的 ``data``、以及前端任务面板读取（与 Planner ``validate_contract`` 工具一致）。
    """
    if not isinstance(result, dict):
        return result
    cr = result.get("customer_result")
    if isinstance(cr, dict):
        mc = cr.get("matched_customer")
        if isinstance(mc, dict):
            disp = (mc.get("customer_name") or mc.get("name") or mc.get("unit_name") or "").strip()
            if disp:
                result["customer_name"] = disp
        elif cr.get("suggestion"):
            sug = str(cr.get("suggestion") or "").strip()
            if sug:
                result["customer_name"] = sug
    vps = result.get("valid_products")
    if isinstance(vps, list) and vps:
        result["products"] = _to_json_safe(vps)
    return result


def validate_customer(customer_name: str) -> dict[str, Any]:
    """快捷函数：校验客户名称"""
    validator = get_validator()
    return validator.validate_customer(customer_name)


def validate_product(model_number: str, product_name: str | None = None) -> dict[str, Any]:
    """快捷函数：校验产品型号"""
    validator = get_validator()
    return validator.validate_product(model_number, product_name)