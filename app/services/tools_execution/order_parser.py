from __future__ import annotations

import logging
import re

from app.services.tools_execution.order_parser_helpers import (
    build_missing_prompt,
    cleanup_unit_name,
    normalize_chinese_digits,
    normalize_model_number_token,
    normalize_quantity_token,
    normalize_trailing_unit_name,
    parse_cn_number,
)

logger = logging.getLogger(__name__)


def _parse_order_text(order_text: str) -> dict:
    try:
        original_text = (order_text or "").strip()

        text = original_text
        for kw in ["发货单", "送货单", "出货单"]:
            text = text.replace(kw, " ")

        text = (
            text.replace("。", " ")
            .replace("，", " ")
            .replace(",", " ")
            .replace("、", " ")
            .replace("：", " ")
            .replace(":", " ")
        )

        text = text.replace("的规格", "规格")
        slot_text = (
            original_text.replace("。", " ")
            .replace("，", " ")
            .replace(",", " ")
            .replace("、", " ")
            .replace("：", " ")
            .replace(":", " ")
            .replace("的规格", "规格")
        )

        if not text:
            return {"success": False, "message": "订单文本格式不正确，缺少内容"}

        slot_model = None
        slot_spec = None
        slot_qty_tins = None

        model_token_pattern = r"[0-9A-Za-z-]{3,16}"
        m_model = re.search(
            rf"(?:编号|型号)\s*(?:是)?\s*[:：]?\s*({model_token_pattern})", slot_text
        )
        if m_model:
            slot_model = (m_model.group(1) or "").strip().upper()
        else:
            m_model2 = re.search(rf"({model_token_pattern})\s*(?:的)?\s*规格", slot_text)
            if m_model2:
                slot_model = (m_model2.group(1) or "").strip().upper()

        if "规格" in slot_text:
            after_spec = slot_text.split("规格", 1)[1]
            number_token_pattern = r"(?:\d+(?:\.\d+)?|[一二两三四五六七八九]?十[一二三四五六七八九]?|[一二两三四五六七八九零〇])"
            qty_token_pattern = r"(?:\d+|[一二两三四五六七八九十零〇两]+)"

            m_spec_qty = re.search(
                rf"^\s*[:：]?\s*({number_token_pattern})(?:\s*(?:要|来|拿|共|一共|总共)?\s*({qty_token_pattern})\s*桶)?",
                after_spec,
            )
            if m_spec_qty:
                spec_num = parse_cn_number(m_spec_qty.group(1))
                if spec_num is not None:
                    slot_spec = float(spec_num)
                if m_spec_qty.group(2):
                    qty_num = parse_cn_number(m_spec_qty.group(2))
                    if qty_num is not None:
                        slot_qty_tins = int(qty_num)
            else:
                m_spec = re.search(r"^\s*[:：]?\s*(\d+(?:\.\d+)?)", after_spec)
                if m_spec:
                    spec_num = parse_cn_number(m_spec.group(1))
                    if spec_num is not None:
                        slot_spec = float(spec_num)
                else:
                    m_spec_cn = re.search(
                        r"^\s*[:：]?\s*([一二两三四五六七八九]?十[一二三四五六七八九]?|[一二两三四五六七八九零〇])",
                        after_spec,
                    )
                    if m_spec_cn:
                        spec_num = parse_cn_number(m_spec_cn.group(1))
                        if spec_num is not None:
                            slot_spec = float(spec_num)

        if slot_qty_tins is None:
            m_qty = re.search(
                r"(?:一共|总共|共|要|来|拿)?\s*(\d+|[一二两三四五六七八九十零〇两]+)\s*桶",
                slot_text,
            )
            if m_qty:
                qty_num = parse_cn_number(m_qty.group(1))
                if qty_num is not None:
                    slot_qty_tins = int(qty_num)

        unit_candidate = slot_text
        unit_candidate = re.sub(r"(发货单|送货单|出货单)", " ", unit_candidate)
        unit_candidate = re.sub(
            rf"(?:编号|型号)\s*(?:是)?\s*[:：]?\s*{model_token_pattern}", " ", unit_candidate
        )
        unit_candidate = re.sub(
            r"规格\s*[:：]?\s*(?:\d+(?:\.\d+)?|[一二两三四五六七八九十零〇两]+)(?:\s*(?:\d+|[一二两三四五六七八九十零〇两]+)\s*桶)?",
            " ",
            unit_candidate,
        )
        unit_candidate = re.sub(
            r"(?:一共|总共|共|要|来|拿)?\s*(?:\d+|[一二两三四五六七八九十零〇两]+)\s*桶",
            " ",
            unit_candidate,
        )
        unit_candidate = re.sub(r"[0-9A-Za-z-]{3,16}", " ", unit_candidate)
        unit_candidate = re.sub(r"[，,\s]+", " ", unit_candidate).strip()
        slot_unit = cleanup_unit_name(unit_candidate)
        if not slot_unit:
            m_unit = re.search(
                r"(?:打印(?:一下)?)\s*([^，,。]+?)\s*的?\s*(?:发货单|送货单|出货单)", slot_text
            )
            if not m_unit:
                m_unit = re.search(r"([^，,。]+?)\s*的?\s*(?:发货单|送货单|出货单)", slot_text)
            if m_unit:
                slot_unit = cleanup_unit_name(m_unit.group(1))
        if not slot_unit:
            m_unit3 = re.search(r"([^，,。0-9]+?)的(?:发货单|送货单|出货单)", slot_text)
            if m_unit3:
                slot_unit = cleanup_unit_name(m_unit3.group(1))
        if not slot_unit:
            for bill_kw in ["发货单", "送货单", "出货单"]:
                if bill_kw in slot_text:
                    slot_unit = cleanup_unit_name(slot_text.split(bill_kw)[0])
                    if slot_unit:
                        break
        if not slot_unit:
            m_unit4 = re.search(
                r"打印(?:一下)?\s*([^，,。]+?)\s*(?:发货单|送货单|出货单)", slot_text
            )
            if m_unit4:
                slot_unit = cleanup_unit_name(m_unit4.group(1))

        if slot_unit and slot_qty_tins is not None:
            try:
                qt = int(slot_qty_tins)
            except (TypeError, ValueError):
                qt = None
            if qt is not None and qt > 0:
                tu = str(slot_unit).strip()
                tail = str(qt)
                if tu.endswith(tail) and len(tu) > len(tail):
                    pref = tu[: -len(tail)].strip()
                    if pref and re.search(r"[\u4e00-\u9fa5A-Za-z]", pref):
                        slot_unit = pref

        slot_mode_trigger = (
            (
                "编号" in slot_text
                or "型号" in slot_text
                or "一共" in slot_text
                or "总共" in slot_text
                or "共" in slot_text
            )
            or re.search(rf"{model_token_pattern}\s*(?:的)?\s*规格", slot_text)
            or re.search(r"(?:要|来|拿)\s*(?:\d+|[一二两三四五六七八九十零〇两]+)\s*桶", slot_text)
        )
        multi_product_hint = (
            len(
                re.findall(
                    r"(?:\d+|[一二两三四五六七八九十零〇]+)\s*桶\s*[0-9A-Za-z-]+\s*规格\s*\d+(?:\.\d+)?",
                    slot_text,
                )
            )
            >= 2
        )
        if (
            slot_mode_trigger
            and (slot_model or slot_spec or slot_qty_tins)
            and not multi_product_hint
        ):
            missing_prompt = build_missing_prompt(
                unit_name=slot_unit,
                model_number=slot_model,
                tin_spec=(
                    int(slot_spec)
                    if isinstance(slot_spec, float) and slot_spec.is_integer()
                    else slot_spec
                ),
                quantity_tins=slot_qty_tins,
            )
            if missing_prompt:
                return {"success": False, "message": missing_prompt}

            return {
                "success": True,
                "unit_name": slot_unit,
                "products": [
                    {
                        "name": "",
                        "model_number": str(slot_model),
                        "quantity_tins": int(slot_qty_tins),
                        "tin_spec": float(slot_spec),
                    }
                ],
            }

        multi_pattern = (
            r"(\d+|[一二两三四五六七八九十零〇]+)\s*桶\s*([0-9A-Za-z-]+)\s*规格\s*(\d+(?:\.\d+)?)"
        )
        multi_matches = list(re.finditer(multi_pattern, slot_text))
        if multi_matches:
            products = []
            for m in multi_matches:
                qty = parse_cn_number(m.group(1))
                model = (m.group(2) or "").strip().upper()
                spec = float(m.group(3))
                if model:
                    products.append(
                        {
                            "name": "",
                            "model_number": model,
                            "quantity_tins": int(qty) if qty else 1,
                            "tin_spec": spec,
                        }
                    )

            if products:
                prefix_text = slot_text[: multi_matches[0].start()]
                for kw in [
                    "发货单",
                    "送货单",
                    "出货单",
                    "货单",
                    "打印",
                    "打单",
                    "开单",
                    "帮我",
                    "给我",
                    "请",
                    "一下",
                ]:
                    prefix_text = prefix_text.replace(kw, " ")
                unit_candidate = cleanup_unit_name(prefix_text)
                if not unit_candidate:
                    unit_candidate = cleanup_unit_name(text.split()[0] if text.split() else "")

                if unit_candidate:
                    return {"success": True, "unit_name": unit_candidate, "products": products}

        patterns = [
            r"^([^\d]+?)(\d+|[一二三四五六七八九十零〇两]+)\s*桶\s*(.+?)\s*规格\s*(\d+(?:\.\d+)?)",
            r"^([^\d]+?)(\d+|[一二三四五六七八九十零〇两]+)\s*桶\s*(.+)$",
            r"^([^\d]+?)(\d+|[一二三四五六七八九十零〇两]+)\s*(箱|件)\s*(.+)",
            r"^([^\d]+?)(\d+(?:\.\d+)?|[一二三四五六七八九十零〇两]+)\s*(公斤|kg)\s*(.+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                if len(groups) >= 3:
                    unit_name = normalize_trailing_unit_name(groups[0])

                    unit_or_measure = (groups[2] or "").strip()
                    if unit_or_measure in ["箱", "件", "公斤", "kg"]:
                        try:
                            if unit_or_measure in ["箱", "件"]:
                                quantity = float(normalize_quantity_token(groups[1]) or 0)
                            else:
                                token = (groups[1] or "").strip()
                                if re.fullmatch(r"\d+(?:\.\d+)?", token):
                                    quantity = float(token)
                                else:
                                    digits = normalize_chinese_digits(token)
                                    quantity = float(digits) if digits else float(token)
                        except:
                            quantity = 1

                        product_name = groups[3].strip() if len(groups) > 3 else "产品"

                        result = {
                            "success": True,
                            "unit_name": unit_name,
                            "products": [
                                {
                                    "name": product_name,
                                    "tin_spec": 10.0,
                                }
                            ],
                        }

                        if "公斤" in unit_or_measure or "kg" in unit_or_measure:
                            result["products"][0]["quantity_kg"] = quantity
                        else:
                            result["products"][0]["quantity_tins"] = (
                                int(quantity) if unit_or_measure in ["箱", "件"] else quantity
                            )

                        return result
                    else:
                        try:
                            quantity = normalize_quantity_token(groups[1])
                            if quantity is None:
                                return {"success": False, "message": "解析数字失败（数量无法识别）"}

                            model_number = normalize_model_number_token(groups[2])
                            if not model_number:
                                return {"success": False, "message": "解析数字失败（型号无法识别）"}

                            spec = float(groups[3]) if len(groups) > 3 else 10.0
                        except:
                            return {"success": False, "message": "解析数字失败"}

                        return {
                            "success": True,
                            "unit_name": unit_name,
                            "products": [
                                {
                                    "name": "",
                                    "model_number": model_number,
                                    "quantity_tins": quantity,
                                    "tin_spec": spec,
                                }
                            ],
                        }

        has_container_qty = any(k in text for k in ["桶", "箱", "件", "公斤", "kg"])
        if not has_container_qty:
            m = re.search(rf"([^\d]+?)\s*({model_token_pattern})\s*规格\s*(\d+(?:\.\d+)?)", text)
            if m:
                unit_part = m.group(1)
                model_token = m.group(2)
                spec_token = m.group(3)

                unit_name = normalize_trailing_unit_name(unit_part)
                unit_name = re.sub(r"^(帮我|给我)?打印(一下)?|^打单|^开单", "", unit_name).strip()
                model_number = normalize_model_number_token(model_token)
                tin_spec = float(spec_token)

                if unit_name and model_number and tin_spec is not None:
                    spec_display = int(tin_spec) if tin_spec.is_integer() else tin_spec
                    return {
                        "success": False,
                        "message": f"还缺少桶数（数量）。已识别：{unit_name} / {model_number} / 规格 {spec_display}。请告诉我需要多少桶？",
                    }

        try:
            import json
            import os

            import httpx

            api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
            if api_key:
                prompt = (
                    "请从下面中文订单口语中抽取 JSON 字段："
                    "unit_name, model_number, tin_spec, quantity_tins。"
                    "仅返回 JSON，不要解释，不要 markdown。\n"
                    f"文本：{text}"
                )
                from app.infrastructure.llm.providers.credentials import (
                    default_chat_completions_url,
                )

                with httpx.Client(timeout=8.0) as client:
                    resp = client.post(
                        default_chat_completions_url(),
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": "deepseek-chat",
                            "messages": [
                                {
                                    "role": "system",
                                    "content": "你是结构化信息抽取助手，只输出 JSON。",
                                },
                                {"role": "user", "content": prompt},
                            ],
                            "temperature": 0.0,
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        content = (
                            (data.get("choices") or [{}])[0]
                            .get("message", {})
                            .get("content", "")
                            .strip()
                        )
                        content = re.sub(r"^```json\s*|^```\s*|```$", "", content).strip()
                        parsed = json.loads(content) if content else {}
                        ai_unit = cleanup_unit_name(str(parsed.get("unit_name", "")).strip())
                        ai_model = str(parsed.get("model_number", "")).strip()
                        ai_spec_raw = str(parsed.get("tin_spec", "")).strip()
                        ai_qty_raw = str(parsed.get("quantity_tins", "")).strip()
                        ai_spec = parse_cn_number(ai_spec_raw) if ai_spec_raw else None
                        ai_qty = parse_cn_number(ai_qty_raw) if ai_qty_raw else None

                        missing_prompt = build_missing_prompt(
                            unit_name=ai_unit,
                            model_number=ai_model or None,
                            tin_spec=ai_spec,
                            quantity_tins=int(ai_qty) if ai_qty else None,
                        )
                        if missing_prompt:
                            return {"success": False, "message": missing_prompt}

                        if ai_unit and ai_model and ai_spec and ai_qty:
                            return {
                                "success": True,
                                "unit_name": ai_unit,
                                "products": [
                                    {
                                        "name": "",
                                        "model_number": ai_model,
                                        "quantity_tins": int(ai_qty),
                                        "tin_spec": float(ai_spec),
                                    }
                                ],
                            }
        except Exception as ai_err:
            logger.warning(f"AI 结构化抽取兜底失败，回退规则流程: {ai_err}")

        parts = text.split()
        if len(parts) >= 2:
            unit_name = parts[0].strip()
            return {
                "success": True,
                "unit_name": unit_name,
                "products": [
                    {
                        "name": " ".join(parts[1:]),
                        "quantity_tins": 1,
                        "tin_spec": 10.0,
                    }
                ],
            }

        return {
            "success": False,
            "message": f"无法解析订单文本：{order_text}，请使用格式：发货单 + 单位名 + 数量 + 桶 + 型号 + 规格",
        }

    except Exception as e:
        logger.error(f"解析订单文本失败：{e}")
        return {"success": False, "message": f"解析失败：{str(e)}"}
