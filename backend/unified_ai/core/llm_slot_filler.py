"""
智能槽位填充器 - LLM 增强版（与 ``sales_contract_intent_bridge`` 对齐，避免重复话术）。
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def llm_fill_slots(
    intent: str,
    user_input: str,
    slots: dict[str, Any],
    missing_slots: list[str],
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    使用 LLM 智能填充缺失的槽位。

    ``sales_contract`` 且缺 ``customer_name`` / ``products`` 时，走
    ``sales_contract_intent_bridge`` 单次结构化抽取 + 主数据对齐；其余意图保留旧 JSON 补全。
    """
    if not missing_slots:
        return slots

    if intent == "sales_contract" and (
        "customer_name" in missing_slots or "products" in missing_slots
    ):
        try:
            from backend.sales_contract_intent_bridge import (
                extract_sales_contract_draft,
                merge_bridge_prefill_entities,
                resolve_draft_to_tool_slots,
            )

            merged = merge_bridge_prefill_entities(intent, slots, user_input)
            slots.update(merged)

            draft = extract_sales_contract_draft(user_input)
            if draft:
                resolved = resolve_draft_to_tool_slots(draft, raw_user_message=user_input)
                if resolved:
                    if "customer_name" in missing_slots:
                        slots["customer_name"] = resolved.get("customer_name")
                    if "products" in missing_slots:
                        slots["products"] = resolved.get("products")
                    logger.info("[LLM Slot Filler] bridge 填充: %s", list(slots.keys()))
                    return slots
        except Exception as e:
            logger.warning("[LLM Slot Filler] bridge 填充失败: %s", e)

    try:
        from backend.llm_config import get_llm_client, require_api_key, resolve_chat_model

        try:
            require_api_key()
        except Exception:
            return slots

        client = get_llm_client()
        model = resolve_chat_model()

        prompt = f"""你是一个槽位补全助手。用户输入："{user_input}"
当前已提取的信息：{slots}
需要提取的缺失字段：{missing_slots}

请根据用户输入，尝试提取缺失的字段信息。只返回你能确定的信息，不需要的信息填 null。

返回格式（JSON）：
{{
    "customer_name": "客户名称（如果能确定）",
    "products": ["产品型号列表"],
    "delivery_date": "交货日期（如果能确定）",
    "remark": "备注（如果能确定）"
}}

只返回 JSON，不要其他内容。"""

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=500,
        )

        content = response.choices[0].message.content.strip()

        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        import json

        result = json.loads(content)

        for slot_name in missing_slots:
            if slot_name in result and result[slot_name] is not None:
                slots[slot_name] = result[slot_name]

        logger.info("[LLM Slot Filler] 填充结果: %s", slots)

    except Exception as e:
        logger.warning("[LLM Slot Filler] LLM填充失败: %s", e)

    return slots
