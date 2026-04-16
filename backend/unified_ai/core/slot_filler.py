"""
槽位填充器
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from ..registry.intent_registry import get_intent
from ..utils.metrics import get_metrics

logger = logging.getLogger(__name__)
_MODEL_TOKEN_PATTERN = r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*"
# 口语量词 + 常见「一统」→「一桶」误写
_ORDER_UNIT = r"(?:桶|瓶|罐|支)"
_ORDER_TYPO_FIXES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile("一统"), "一桶"),
    (re.compile("两统"), "两桶"),
    (re.compile("三统"), "三桶"),
    (re.compile("四统"), "四桶"),
    (re.compile("五统"), "五桶"),
)


@dataclass
class SlotFillResult:
    success: bool
    intent: str
    slots: dict[str, Any] = field(default_factory=dict)
    missing_slots: list[str] = field(default_factory=list)
    ambiguous_slots: dict[str, Any] = field(default_factory=dict)
    processing_time_ms: float = 0.0
    error: str = ""


class SlotFiller:
    def __init__(self):
        self._chinese_numbers = {
            "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
            "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
            "百": 100, "千": 1000
        }

    @staticmethod
    def _normalize_order_typos(user_input: str) -> str:
        s = user_input
        for pat, repl in _ORDER_TYPO_FIXES:
            s = pat.sub(repl, s)
        return s

    @staticmethod
    def _model_boundary_match(model: str, text: str) -> bool:
        """避免短型号作为子串误命中（如 1 命中 3100H）。"""
        if not model or not text:
            return False
        esc = re.escape(model)
        return re.search(rf"(?<![A-Za-z0-9]){esc}(?![A-Za-z0-9])", text, re.IGNORECASE) is not None

    async def fill(
        self,
        intent: str,
        entities: dict[str, Any],
        user_input: str,
        context: dict[str, Any] | None = None
    ) -> SlotFillResult:
        import time
        start = time.perf_counter()

        context = context or {}
        intent_def = get_intent(intent)

        if not intent_def:
            return SlotFillResult(
                success=False,
                intent=intent,
                error=f"未知意图: {intent}",
                processing_time_ms=(time.perf_counter() - start) * 1000
            )

        slots = {}
        missing_slots = []
        ambiguous_slots = {}

        for slot_name, slot_def in intent_def.slots.items():
            if slot_name in entities:
                slots[slot_name] = entities[slot_name]
            else:
                extracted = self._extract_slot(slot_name, slot_def, user_input, context)
                if extracted is not None:
                    slots[slot_name] = extracted
                elif slot_def.get("required", False):
                    if context and slot_name in context:
                        slots[slot_name] = context[slot_name]
                    else:
                        missing_slots.append(slot_name)

        if "products" in slots and isinstance(slots["products"], list):
            slots["products"] = self._normalize_products(slots["products"], user_input)

        if intent == "sales_contract":
            cn = str(slots.get("customer_name") or "").strip()
            if cn and user_input:
                try:
                    from backend.sales_contract_intent_bridge import _customer_hint_is_bulk_user_utterance
                    from backend.shared_utils import extract_customer_name, find_matching_customer

                    if _customer_hint_is_bulk_user_utterance(cn):
                        spoken = extract_customer_name(user_input)
                        if spoken:
                            hit = find_matching_customer(spoken)
                            if hit:
                                slots["customer_name"] = hit
                except Exception:
                    pass

        processing_time_ms = (time.perf_counter() - start) * 1000
        get_metrics().histogram("slot_filler.duration_ms", processing_time_ms)
        get_metrics().inc("slot_filler.fill", tags={"intent": intent})

        return SlotFillResult(
            success=len(missing_slots) == 0,
            intent=intent,
            slots=slots,
            missing_slots=missing_slots,
            ambiguous_slots=ambiguous_slots,
            processing_time_ms=processing_time_ms
        )

    def _extract_slot(
        self,
        slot_name: str,
        slot_def: dict[str, Any],
        user_input: str,
        context: dict[str, Any]
    ) -> Any:
        if slot_name == "customer_name":
            return self._extract_customer_name(user_input, context)
        elif slot_name == "products":
            return self._extract_products(user_input, context)
        elif slot_name == "query":
            return self._extract_query(user_input, context)
        elif slot_name == "delivery_date":
            return self._extract_date(user_input)
        elif slot_name == "shipment_id":
            return self._extract_shipment_id(user_input)
        elif slot_name == "status":
            return self._extract_status(user_input)
        elif slot_name == "model_number":
            return self._extract_model_number(user_input, context)
        elif slot_name == "quantity":
            return self._extract_quantity(user_input)
        elif slot_name == "report_type":
            return self._extract_report_type(user_input)
        elif slot_name == "data_type":
            return self._extract_data_type(user_input)
        elif slot_name == "date_range":
            return self._extract_date_range(user_input)
        elif slot_name == "supplier":
            return self._extract_supplier(user_input, context)
        elif slot_name == "approved":
            return self._extract_approved(user_input)
        elif slot_name == "updates":
            return self._extract_updates(user_input)
        elif slot_name == "remark":
            return self._extract_remark(user_input)
        return None

    def _extract_customer_name(self, user_input: str, context: dict) -> str | None:
        try:
            from backend.routers.xcagi_compat import _load_customers_rows
            customers = _load_customers_rows()

            for cust in customers:
                name = cust.get("customer_name") or cust.get("name") or cust.get("unit_name", "")
                if name and name in user_input:
                    return name

            normalized_input = user_input.lower().replace(" ", "")
            for cust in customers:
                name = cust.get("customer_name") or cust.get("name") or cust.get("unit_name", "")
                if name and normalized_input in name.lower().replace(" ", ""):
                    return name

        except Exception as e:
            logger.warning(f"[SlotFiller] 提取客户名失败: {e}")

        try:
            from backend.shared_utils import extract_customer_name

            spoken = extract_customer_name(user_input)
            if spoken:
                return spoken
        except Exception:
            pass

        return None

    def _extract_products(self, user_input: str, context: dict) -> list[dict[str, Any]] | None:
        try:
            from backend.routers.xcagi_compat import _load_products_all_for_export
            products = _load_products_all_for_export(keyword=None, unit=None)

            product_index = {}
            for p in products:
                model = p.get("model_number", "").strip()
                if model:
                    if model not in product_index:
                        product_index[model] = p
                    else:
                        existing = product_index[model]
                        if not existing.get("name") and p.get("name"):
                            product_index[model] = p

            product_models = set(product_index.keys())
            normalized_input = self._normalize_for_match(user_input)
            order_text = self._normalize_order_typos(user_input)

            found = []
            # 首先检查是否有显式的产品型号在输入中
            for model in product_models:
                if not (
                    self._model_boundary_match(model, user_input)
                    or self._model_boundary_match(model, order_text)
                ):
                    continue
                product_info = product_index[model]
                qty = self._extract_quantity_for_text(model, user_input)
                if qty == 1:
                    qty = self._extract_quantity_for_text(model, order_text)
                    if qty == 1:
                        name_alias = str(product_info.get("name") or "").strip()
                        if name_alias and self._normalize_for_match(name_alias) in normalized_input:
                            qty = self._extract_quantity_for_text(name_alias, user_input)
                            if qty == 1:
                                qty = self._extract_quantity_for_text(name_alias, order_text)
                found.append({
                    "model_number": model,
                    "name": product_info.get("name", ""),
                    "spec": product_info.get("specification", "") or product_info.get("spec", ""),
                    "unit": product_info.get("unit", "桶"),
                    "unit_price": str(product_info.get("price", 0)),
                    "quantity": str(qty),
                })

            # 支持按产品名称识别（如“PU天那水(面水) 来三桶”）
            # 同名映射到多个型号时跳过，避免误匹配。
            name_to_models: dict[str, list[str]] = {}
            for model, info in product_index.items():
                name = str(info.get("name") or "").strip()
                if not name:
                    continue
                name_norm = self._normalize_for_match(name)
                if len(name_norm) < 2:
                    continue
                if name_norm not in normalized_input:
                    continue
                name_to_models.setdefault(name_norm, []).append(model)

            for name_norm, models in sorted(name_to_models.items(), key=lambda kv: len(kv[0]), reverse=True):
                if len(models) != 1:
                    continue
                model = models[0]
                if any(p.get("model_number") == model for p in found):
                    continue
                product_info = product_index[model]
                alias_name = str(product_info.get("name") or "").strip()
                qty = self._extract_quantity_for_text(alias_name, user_input)
                if qty == 1:
                    qty = self._extract_quantity_for_text(alias_name, order_text)
                found.append({
                    "model_number": model,
                    "name": product_info.get("name", ""),
                    "spec": product_info.get("specification", "") or product_info.get("spec", ""),
                    "unit": product_info.get("unit", "桶"),
                    "unit_price": str(product_info.get("price", 0)),
                    "quantity": str(qty),
                })

            # 尝试用正则表达式提取"X 桶 XXX"格式，覆盖默认数量
            # 匹配"两桶 3721"、"一桶 308"、"需要三桶 779"等格式
            # 使用非贪婪匹配，正确提取数量
            pattern = (
                rf"(?:需要\s*|要\s*)?(\d+|[零一二两三四五六七八九十百千]+)\s*{_ORDER_UNIT}\s*的?\s*"
                rf"[，,]?\s*(?:编号)?({_MODEL_TOKEN_PATTERN})"
            )
            for match in re.finditer(pattern, order_text):
                qty_str = match.group(1)
                model = match.group(2)
                # 确保数量是纯数字或中文数字，不是前缀
                if not re.match(r'^(\d+|[零一二两三四五六七八九十百千]+)$', qty_str):
                    continue
                if model in product_models:
                    qty = self._parse_chinese_number(qty_str)
                    product_info = product_index[model]
                    # 更新已存在的产品数量，或添加新产品
                    existing = next((p for p in found if p["model_number"] == model), None)
                    if existing:
                        existing["quantity"] = str(qty)
                    else:
                        found.append({
                            "model_number": model,
                            "name": product_info.get("name", ""),
                            "spec": product_info.get("specification", "") or product_info.get("spec", ""),
                            "unit": product_info.get("unit", "桶"),
                            "unit_price": str(product_info.get("price", 0)),
                            "quantity": str(qty),
                        })

            if not found:
                number_pattern = rf'({_MODEL_TOKEN_PATTERN})\s*[x×]\s*(\d+)'
                for match in re.finditer(number_pattern, order_text):
                    model = match.group(1)
                    qty = int(match.group(2))
                    if model in product_models:
                        product_info = product_index[model]
                        found.append({
                            "model_number": model,
                            "name": product_info.get("name", ""),
                            "spec": product_info.get("specification", "") or product_info.get("spec", ""),
                            "unit": product_info.get("unit", "桶"),
                            "unit_price": str(product_info.get("price", 0)),
                            "quantity": str(qty),
                        })

                quantity_pattern = rf'({_MODEL_TOKEN_PATTERN})\s*(\d+)\s*{_ORDER_UNIT}'
                for match in re.finditer(quantity_pattern, order_text):
                    model = match.group(1)
                    qty = int(match.group(2))
                    if model in product_models:
                        product_info = product_index[model]
                        found.append({
                            "model_number": model,
                            "name": product_info.get("name", ""),
                            "spec": product_info.get("specification", "") or product_info.get("spec", ""),
                            "unit": product_info.get("unit", "桶"),
                            "unit_price": str(product_info.get("price", 0)),
                            "quantity": str(qty),
                        })

            return found if found else None

        except Exception as e:
            logger.warning(f"[SlotFiller] 提取产品失败: {e}")
        return None

    @staticmethod
    def _normalize_for_match(text: str) -> str:
        return "".join(str(text or "").strip().lower().split())

    def _extract_quantity_for_text(self, token: str, user_input: str) -> int:
        token_escaped = re.escape(str(token or "").strip())
        if not token_escaped:
            return 1
        qty_expr = r'(\d+|[零一二两三四五六七八九十百千]+)'
        # 模式 1: "名称×3" / "名称 x 3"
        pattern = rf'{token_escaped}\s*[x×]?\s*(\d+)'
        match = re.search(pattern, user_input)
        if match:
            return int(match.group(1))

        for unit in ("桶", "瓶", "罐", "支"):
            # 模式 2: "三桶 型号" / "三瓶 慢干水" / "一桶的 3706-50F"
            pattern = rf'{qty_expr}\s*{unit}\s*的?\s*[，,]?\s*{token_escaped}'
            match = re.search(pattern, user_input)
            if match:
                return self._parse_chinese_number(match.group(1))

            # 模式 3: "型号 … 三桶" / "慢干水三瓶"
            pattern = rf'{token_escaped}.*?{qty_expr}\s*{unit}'
            match = re.search(pattern, user_input)
            if match:
                return self._parse_chinese_number(match.group(1))

            # 模式 4: "需要三桶 型号"
            pattern = rf'需要\s*{qty_expr}\s*{unit}\s*的?\s*[，,]?\s*{token_escaped}'
            match = re.search(pattern, user_input)
            if match:
                return self._parse_chinese_number(match.group(1))
        return 1

    def _extract_quantity_for_model(self, model: str, user_input: str) -> int:
        return self._extract_quantity_for_text(model, user_input)

    def _parse_chinese_number(self, text: str) -> int:
        if text.isdigit():
            return int(text)
        if text in self._chinese_numbers:
            return self._chinese_numbers[text]
        # 处理"十一"、"十二"等
        if '十' in text:
            if text == '十':
                return 10
            parts = text.split('十')
            ten_part = self._chinese_numbers.get(parts[0], 1) if parts[0] else 1
            one_part = self._chinese_numbers.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
            return ten_part * 10 + one_part
        return 1

    def _extract_date(self, user_input: str) -> str | None:
        date_pattern = r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)'
        match = re.search(date_pattern, user_input)
        if match:
            return match.group(1)
        return None

    def _extract_query(self, user_input: str, context: dict) -> str | None:
        try:
            from backend.routers.xcagi_compat import _load_products_all_for_export
            products = _load_products_all_for_export(keyword=None, unit=None)

            product_models = set()
            product_name_to_model: dict[str, str] = {}
            for p in products:
                model = p.get("model_number", "").strip()
                if model:
                    product_models.add(model)
                name = str(p.get("name") or "").strip()
                if name:
                    product_name_to_model[self._normalize_for_match(name)] = model

            number_pattern = rf'({_MODEL_TOKEN_PATTERN})'
            for match in re.finditer(number_pattern, user_input):
                model = match.group(1)
                if model in product_models:
                    return model

            for model in product_models:
                if model in user_input:
                    return model

            normalized_input = self._normalize_for_match(user_input)
            for name_norm, model in product_name_to_model.items():
                if name_norm and len(name_norm) >= 2 and name_norm in normalized_input and model:
                    return model

        except Exception as e:
            logger.warning(f"[SlotFiller] 提取query失败: {e}")

        return None

    def _extract_shipment_id(self, user_input: str) -> str | None:
        match = re.search(r'(FH|fh)\d+', user_input)
        if match:
            return match.group(0).upper()
        match = re.search(r'发货单[编号：:]?\s*(\S+)', user_input)
        if match:
            return match.group(1).strip()
        return None

    def _extract_status(self, user_input: str) -> str | None:
        status_map = {
            "待发货": "待发货",
            "已发货": "已发货",
            "已完成": "已完成",
            "待审核": "待审核",
            "已审核": "已审核",
            "pending": "待发货",
            "shipped": "已发货",
            "completed": "已完成",
        }
        for keyword, status in status_map.items():
            if keyword in user_input:
                return status
        return None

    def _extract_model_number(self, user_input: str, context: dict) -> str | None:
        try:
            from backend.routers.xcagi_compat import _load_products_all_for_export
            products = _load_products_all_for_export(keyword=None, unit=None)

            product_models = set()
            product_name_to_model: dict[str, str] = {}
            for p in products:
                model = p.get("model_number", "").strip()
                if model:
                    product_models.add(model)
                name = str(p.get("name") or "").strip()
                if name:
                    product_name_to_model[self._normalize_for_match(name)] = model

            for model in product_models:
                if model in user_input:
                    return model

            number_pattern = rf'({_MODEL_TOKEN_PATTERN})'
            for match in re.finditer(number_pattern, user_input):
                model = match.group(1)
                if model in product_models:
                    return model

            normalized_input = self._normalize_for_match(user_input)
            for name_norm, model in product_name_to_model.items():
                if name_norm and len(name_norm) >= 2 and name_norm in normalized_input and model:
                    return model
        except Exception:
            pass
        return None

    def _extract_quantity(self, user_input: str) -> int | None:
        match = re.search(r'(\d+)\s*(张|个|份|桶|箱|件)', user_input)
        if match:
            return int(match.group(1))
        for cn, num in self._chinese_numbers.items():
            pattern = rf'{cn}\s*(张|个|份|桶|箱|件)'
            if re.search(pattern, user_input):
                return num
        return None

    def _extract_report_type(self, user_input: str) -> str | None:
        type_map = {
            "销售": "sales",
            "库存": "stock",
            "发货": "shipment",
            "采购": "purchase",
        }
        for keyword, rtype in type_map.items():
            if keyword in user_input:
                return rtype
        return "sales"

    def _extract_data_type(self, user_input: str) -> str | None:
        type_map = {
            "客户": "customers",
            "产品": "products",
            "发货单": "shipments",
            "原材料": "materials",
            "库存": "stock",
        }
        for keyword, dtype in type_map.items():
            if keyword in user_input:
                return dtype
        return None

    def _extract_date_range(self, user_input: str) -> str | None:
        match = re.search(r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})\s*[到至~\-]\s*(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})', user_input)
        if match:
            return f"{match.group(1)} ~ {match.group(2)}"
        match = re.search(r'(本月|上月|本季度|上季度|本年|去年|今年)', user_input)
        if match:
            return match.group(1)
        return None

    def _extract_supplier(self, user_input: str, context: dict) -> str | None:
        match = re.search(r'(供应商|供货商)[是为：:]\s*(\S+)', user_input)
        if match:
            return match.group(2).strip()
        return None

    def _extract_approved(self, user_input: str) -> bool | None:
        if re.search(r'(通过|批准|审核通过|同意)', user_input):
            return True
        if re.search(r'(拒绝|驳回|不通过|否决)', user_input):
            return False
        return True

    def _extract_updates(self, user_input: str) -> dict[str, Any] | None:
        updates = {}
        status = self._extract_status(user_input)
        if status:
            updates["status"] = status
        qty_match = re.search(r'数量[是为：:]\s*(\d+)', user_input)
        if qty_match:
            updates["quantity"] = int(qty_match.group(1))
        remark = self._extract_remark(user_input)
        if remark:
            updates["remark"] = remark
        return updates if updates else None

    def _extract_remark(self, user_input: str) -> str | None:
        match = re.search(r'(备注|说明|注意)[是为：:]\s*(.+)', user_input)
        if match:
            return match.group(2).strip()
        return None

    def _normalize_products(self, products: list, user_input: str) -> list[dict[str, Any]]:
        def parse_qty(val):
            if isinstance(val, int):
                return max(1, val)
            if isinstance(val, str):
                import re
                m = re.search(r'(\d+)', val)
                return max(1, int(m.group(1))) if m else 1
            return 1

        normalized = []
        for p in products:
            if isinstance(p, dict):
                normalized.append({
                    "model_number": str(p.get("model_number", "")),
                    "quantity": parse_qty(p.get("quantity", 1))
                })
            elif isinstance(p, str):
                qty = self._extract_quantity_for_model(p, user_input)
                normalized.append({"model_number": p, "quantity": qty})
        return normalized


_slot_filler: SlotFiller | None = None


def get_slot_filler() -> SlotFiller:
    global _slot_filler
    if _slot_filler is None:
        _slot_filler = SlotFiller()
    return _slot_filler
