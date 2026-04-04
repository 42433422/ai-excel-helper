from __future__ import annotations

import difflib
import re
from typing import Any, Callable, Dict, List, Tuple

from app.bootstrap import get_shipment_app_service
from app.db.models import Product
from app.db.session import get_db


class ShipmentNumberModeService:
    """
    XCAGI 内部编号模式编排服务。
    - 统一使用 XCAGI DB（purchase_units/products/customer_products）
    - 不依赖外部 98k 或 unit_databases/*.db
    - 失败时按严格策略返回错误，不走预览兜底
    """

    MODIFY_VERB_PATTERN = re.compile(
        r"(再加|还要|继续加|再补|加上|增加|减少|减去|删掉|删除|去掉|移除|改成|改为|改)"
    )

    @staticmethod
    def _normalize_unit_name(value: str) -> str:
        text = str(value or "").strip().lower()
        if not text:
            return ""
        text = re.sub(r"(有限责任公司|有限公司|公司|家私|家具|商贸|贸易|建材|装饰)", "", text)
        text = re.sub(r"[\s\-_()（）【】\[\]·,，.。/\\]+", "", text)
        return text

    def _query_active_purchase_unit_names(self) -> List[str]:
        from app.db.session import get_db
        from app.db.models.purchase_unit import PurchaseUnit

        with get_db() as db:
            rows = (
                db.query(PurchaseUnit.unit_name)
                .filter(PurchaseUnit.is_active == True)
                .order_by(PurchaseUnit.unit_name.asc())
                .all()
            )
            return [str(r[0]).strip() for r in rows if r and str(r[0]).strip()]

    def _resolve_unit_alias(self, typed_unit: str, unit_pool: List[str]) -> str:
        typed = (typed_unit or "").strip()
        if not typed or not unit_pool:
            return ""

        # 兼容口语尾巴把数量粘到单位名（如“蕊芯1”“七彩乐园一”）：
        # 优先用原始文本匹配，失败后再对尾部数量噪声做清洗并重试。
        candidate_typed_list = [typed]
        stripped_qty_tail = re.sub(r"(?:\d+|[一二两三四五六七八九十零〇]+)\s*$", "", typed).strip()
        if stripped_qty_tail and stripped_qty_tail not in candidate_typed_list:
            candidate_typed_list.append(stripped_qty_tail)

        normalized_candidates = []
        for item in candidate_typed_list:
            normalized_item = self._normalize_unit_name(item)
            if normalized_item and normalized_item not in normalized_candidates:
                normalized_candidates.append(normalized_item)
        if not normalized_candidates:
            return ""

        def _tail_digits(value: str) -> str:
            match = re.search(r"(\d+)$", str(value or ""))
            return match.group(1) if match else ""

        for normalized_typed in normalized_candidates:
            normalized_exact = [
                unit for unit in unit_pool
                if self._normalize_unit_name(unit) == normalized_typed
            ]
            if len(normalized_exact) == 1:
                return normalized_exact[0]

            contains = [
                unit for unit in unit_pool
                if normalized_typed in self._normalize_unit_name(unit)
                or self._normalize_unit_name(unit) in normalized_typed
            ]
            if len(contains) == 1:
                return contains[0]
            if len(contains) > 1:
                # 若用户输入带尾号（如“蕊芯1”），优先匹配同尾号单位（如“蕊芯家私1”）。
                typed_digits = _tail_digits(normalized_typed)
                if typed_digits:
                    digit_matched = [
                        unit
                        for unit in contains
                        if _tail_digits(self._normalize_unit_name(unit)) == typed_digits
                    ]
                    if len(digit_matched) == 1:
                        return digit_matched[0]
                    if len(digit_matched) > 1:
                        contains = digit_matched

            scored = []
            for unit in contains or unit_pool:
                normalized_unit = self._normalize_unit_name(unit)
                if not normalized_unit:
                    continue
                score = difflib.SequenceMatcher(None, normalized_typed, normalized_unit).ratio()
                scored.append((score, unit))
            scored.sort(key=lambda item: item[0], reverse=True)
            if not scored:
                continue

            top_score, top_name = scored[0]
            second_score = scored[1][0] if len(scored) > 1 else 0.0
            if top_score >= 0.86 and (top_score - second_score) >= 0.08:
                return top_name
        return ""

    def _extract_existing_unit_from_modify_text(self, text: str, all_units: List[str]) -> str:
        source_text = (text or "").strip()
        if not source_text or not all_units:
            return ""
        action_match = self.MODIFY_VERB_PATTERN.search(source_text)
        if not action_match:
            return ""
        prefix = source_text[:action_match.start()]
        matches = [unit for unit in all_units if unit and unit in prefix]
        if not matches:
            return ""
        matches.sort(key=len, reverse=True)
        return matches[0]

    def _parse_by_db_terms(
        self,
        *,
        text: str,
        unit_pool: List[str],
        model_pool: List[str],
    ) -> Dict[str, Any]:
        """
        基于 XCAGI 实际词条做轻量解析：
        - 单位：最长子串命中 purchase_units
        - 型号：优先命中 products.model_number
        - 规格/桶数：从“规格X”“X桶”抽取
        """
        raw = str(text or "").strip()
        if not raw:
            return {"success": False, "message": "订单文本为空", "unit_name": "", "products": []}

        def _pick_unit_name(source: str) -> str:
            hits = [u for u in unit_pool if u and u in source]
            if not hits:
                return ""
            hits.sort(key=len, reverse=True)
            return hits[0]

        def _pick_model_number(source: str) -> str:
            upper_source = source.upper()
            hits = [m for m in model_pool if m and m in upper_source]
            if not hits:
                return ""
            # 避免短型号误命中（如 980 命中 9803）
            hits.sort(key=len, reverse=True)
            return hits[0]

        unit_name = _pick_unit_name(raw)
        model_number = _pick_model_number(raw)

        m_spec = re.search(r"(?:规格|规)\s*[:：]?\s*(\d+(?:\.\d+)?)", raw)
        m_qty = re.search(r"(\d+(?:\.\d+)?)\s*桶", raw)
        if not m_qty:
            m_qty = re.search(r"(?:要|来|拿|共|一共|总共)\s*(\d+(?:\.\d+)?)", raw)

        tin_spec = float(m_spec.group(1)) if m_spec else None
        quantity_tins = int(float(m_qty.group(1))) if m_qty else None

        # 允许“9803 24 1桶”这类无“规格”关键词的口语输入。
        if tin_spec is None and model_number:
            number_tokens = re.findall(r"\d+(?:\.\d+)?", raw)
            filtered_tokens = []
            for token in number_tokens:
                if token.upper() == model_number:
                    continue
                if quantity_tins is not None and float(token) == float(quantity_tins):
                    continue
                filtered_tokens.append(token)
            if filtered_tokens:
                try:
                    tin_spec = float(filtered_tokens[0])
                except Exception:
                    tin_spec = None

        if not (unit_name and model_number and tin_spec and quantity_tins):
            missing = []
            if not unit_name:
                missing.append("单位")
            if not model_number:
                missing.append("型号")
            if not tin_spec:
                missing.append("规格")
            if not quantity_tins:
                missing.append("桶数")
            return {
                "success": False,
                "message": f"DB词条解析未完整命中，缺少：{'、'.join(missing)}",
                "unit_name": unit_name,
                "products": [],
            }

        return {
            "success": True,
            "unit_name": unit_name,
            "products": [
                {
                    "product_name": model_number,
                    "model_number": model_number,
                    "quantity_tins": quantity_tins,
                    "tin_spec": tin_spec,
                }
            ],
            "message": "ok",
        }

    def _build_unit_not_found_payload(
        self, typed_unit: str, all_units: List[str]
    ) -> Dict[str, Any]:
        typed = str(typed_unit or "").strip()
        if any(unit == typed for unit in all_units):
            return {}

        contains = [unit for unit in all_units if typed and (typed in unit or unit in typed)]
        fuzzy = difflib.get_close_matches(typed, all_units, n=5, cutoff=0.35) if typed else []
        suggestions: List[str] = []
        for unit in contains + fuzzy:
            if unit and unit not in suggestions:
                suggestions.append(unit)
            if len(suggestions) >= 5:
                break

        if suggestions:
            suggestion_text = "；".join(f"{idx + 1}){name}" for idx, name in enumerate(suggestions))
            message = (
                f"未找到购买单位：{typed}。"
                f"请确认单位名称后重试，或从候选中选择：{suggestion_text}。"
            )
        else:
            message = (
                f"未找到购买单位：{typed}。"
                "请先创建该购买单位，或输入已存在的单位名称后再生成。"
            )

        return {
            "success": False,
            "message": message,
            "error_code": "purchase_unit_not_found",
            "data": {
                "input_unit_name": typed,
                "candidate_units": suggestions,
                "need_confirm_unit": True,
            },
        }

    @staticmethod
    def _normalize_success_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            return payload

        doc_name = str(payload.get("doc_name") or payload.get("filename") or "").strip()
        file_path = str(payload.get("file_path") or payload.get("filepath") or "").strip()
        final_order_number = str(payload.get("order_number") or "").strip()
        record_id = payload.get("record_id")
        order_id = payload.get("order_id")
        final_record_id = record_id if record_id is not None else order_id
        document = payload.get("document") if isinstance(payload.get("document"), dict) else {}

        if doc_name and not document.get("filename"):
            document["filename"] = doc_name
        if file_path and not document.get("filepath"):
            document["filepath"] = file_path
        if final_order_number and not document.get("order_number"):
            document["order_number"] = final_order_number
        if final_record_id is not None:
            document["record_id"] = final_record_id
            document["order_id"] = final_record_id

        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        if doc_name:
            data["doc_name"] = doc_name
        if file_path:
            data["file_path"] = file_path
        if final_order_number:
            data["order_number"] = final_order_number
            payload["order_number"] = final_order_number
        if final_record_id is not None:
            payload["record_id"] = final_record_id
            payload["order_id"] = final_record_id
            data["record_id"] = final_record_id
            data["order_id"] = final_record_id
        if document:
            payload["document"] = document
            data["document"] = document

        payload["data"] = data
        return payload

    def execute(
        self,
        *,
        order_text: str,
        custom_order_number: str,
        direct_unit_name: str,
        direct_products: List[Dict[str, Any]],
        parse_order_text: Callable[[str], Dict[str, Any]],
    ) -> Tuple[Dict[str, Any], int]:
        text = str(order_text or "").strip()
        if not text and not (direct_unit_name and direct_products):
            return {
                "success": False,
                "message": "缺少订单文本参数，请提供订单信息",
                "error_code": "missing_order_text",
            }, 400

        unit_pool = self._query_active_purchase_unit_names()
        unit_to_use = str(direct_unit_name or "").strip()
        parsed = {"success": False, "unit_name": "", "products": []}

        model_pool: List[str] = []
        if text:
            parsed = parse_order_text(text) or {}

            # 解析失败时，补一层“XCAGI DB 词条解析”。
            if not parsed.get("success"):
                with get_db() as db:
                    model_rows = (
                        db.query(Product.model_number)
                        .filter((Product.is_active == 1) | (Product.is_active == True) | (Product.is_active.is_(None)))
                        .all()
                    )
                model_pool = [
                    str(row[0] or "").strip().upper()
                    for row in model_rows
                    if row and str(row[0] or "").strip()
                ]
                parsed_by_db = self._parse_by_db_terms(
                    text=text,
                    unit_pool=unit_pool,
                    model_pool=model_pool,
                )
                if parsed_by_db.get("success"):
                    parsed = parsed_by_db

            if not unit_to_use and parsed.get("success"):
                unit_to_use = str(parsed.get("unit_name") or "").strip()

        is_modify_request = bool(self.MODIFY_VERB_PATTERN.search(text))
        if is_modify_request:
            recovered = self._extract_existing_unit_from_modify_text(text, unit_pool)
            if recovered:
                unit_to_use = recovered

        if not unit_to_use and is_modify_request:
            return {
                "success": False,
                "message": "检测到增删改请求，但未识别到购买单位。请先明确单位，例如：七彩乐园再加1桶9803规格28。",
                "error_code": "purchase_unit_required_for_modify",
                "data": {"need_confirm_unit": True},
            }, 400

        if unit_to_use:
            resolved_alias = self._resolve_unit_alias(unit_to_use, unit_pool)
            if resolved_alias:
                unit_to_use = resolved_alias
            unit_not_found = self._build_unit_not_found_payload(unit_to_use, unit_pool)
            if unit_not_found:
                return unit_not_found, 400

        products = list(direct_products or [])
        if not products:
            if not parsed.get("success"):
                return {
                    "success": False,
                    "message": (
                        "编号模式解析失败，已按严格策略停止生成（未启用预览兜底）。"
                        f" 失败原因：{parsed.get('message', '无法解析订单信息')}"
                    ),
                    "error_code": "NUMBER_MODE_STRICT_FAILED",
                    "data": {"parsed_data": parsed},
                }, 400
            products = list(parsed.get("products") or [])

        if not products or not unit_to_use:
            return {
                "success": False,
                "message": "编号模式解析失败，已按严格策略停止生成（未启用预览兜底）。 失败原因：无法解析订单信息",
                "error_code": "NUMBER_MODE_STRICT_FAILED",
                "data": {"parsed_data": parsed},
            }, 400

        # 严格策略：产品必须具备“型号/数量/规格”，且型号须可在 XCAGI products 主库匹配。
        with get_db() as db:
            product_rows = (
                db.query(Product.model_number, Product.name)
                .filter((Product.is_active == 1) | (Product.is_active == True) | (Product.is_active.is_(None)))
                .all()
            )

        model_set = {
            str(model or "").strip().upper()
            for model, _name in product_rows
            if str(model or "").strip()
        }
        name_pool = {
            str(name or "").strip()
            for _model, name in product_rows
            if str(name or "").strip()
        }

        for idx, product in enumerate(products, start=1):
            model_number = str(product.get("model_number") or "").strip().upper()
            product_name = str(product.get("product_name") or product.get("name") or "").strip()
            tin_spec = str(product.get("tin_spec") or product.get("specification") or "").strip()
            quantity = product.get("quantity_tins") or product.get("quantity")

            try:
                quantity_value = float(quantity)
            except Exception:
                quantity_value = 0.0

            if not model_number:
                return {
                    "success": False,
                    "message": f"编号模式解析失败，已按严格策略停止生成（未启用预览兜底）。 失败原因：第{idx}项型号缺失。",
                    "error_code": "NUMBER_MODE_STRICT_FAILED",
                    "data": {"parsed_data": parsed},
                }, 400
            if not tin_spec:
                return {
                    "success": False,
                    "message": f"编号模式解析失败，已按严格策略停止生成（未启用预览兜底）。 失败原因：第{idx}项规格缺失。",
                    "error_code": "NUMBER_MODE_STRICT_FAILED",
                    "data": {"parsed_data": parsed},
                }, 400
            if quantity_value <= 0:
                return {
                    "success": False,
                    "message": f"编号模式解析失败，已按严格策略停止生成（未启用预览兜底）。 失败原因：第{idx}项数量缺失或无效。",
                    "error_code": "NUMBER_MODE_STRICT_FAILED",
                    "data": {"parsed_data": parsed},
                }, 400

            model_matched = model_number in model_set
            if not model_matched:
                return {
                    "success": False,
                    "message": f"编号模式解析失败，已按严格策略停止生成（未启用预览兜底）。 失败原因：型号不存在（{model_number}）。",
                    "error_code": "NUMBER_MODE_STRICT_FAILED",
                    "data": {"parsed_data": parsed, "missing_model_number": model_number},
                }, 400

            if product_name and product_name not in name_pool:
                # 仅提示，不阻断：名称可能存在历史别名，但型号已被主库验证。
                pass

        app_service = get_shipment_app_service()
        result = app_service.generate_shipment_document(
            unit_name=unit_to_use,
            products=products,
            template_name=None,
            order_number=(str(custom_order_number or "").strip() or None),
        )
        result = self._normalize_success_payload(result)

        if result.get("success"):
            return result, 200

        return {
            "success": False,
            "message": (
                "编号模式解析失败，已按严格策略停止生成（未启用预览兜底）。"
                f" 失败原因：{result.get('message', '生成失败')}"
            ),
            "error_code": "NUMBER_MODE_STRICT_FAILED",
            "data": {
                "parsed_data": parsed,
                "detail": result,
            },
        }, 400

