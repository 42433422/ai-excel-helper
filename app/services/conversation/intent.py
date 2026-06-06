import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class IntentMixin:

    def _is_pro_source(self, source: str | None) -> bool:
        normalized = str(source or "").strip().lower().replace("-", "_")
        return normalized in {"pro", "pro_mode", "promode"}

    @staticmethod
    def _normalize_ai_mode(mode: str | None) -> str:
        raw = str(mode or "").strip().lower()
        if raw in {"offline", "local"}:
            return "offline"
        return "online"

    def _resolve_ai_mode(self, user_id: str) -> str:
        try:
            mode_value = self.user_preference_service.get_preference(user_id, "aiMode")
            if mode_value:
                return self._normalize_ai_mode(mode_value)
            legacy_model = self.user_preference_service.get_preference(user_id, "aiModel")
            if legacy_model:
                mode = self._normalize_ai_mode(legacy_model)
                self.user_preference_service.set_preference(user_id, "aiMode", mode)
                return mode
        except Exception as e:
            logger.warning(f"读取 aiMode 偏好失败，回退在线模式: {e}")
        return "online"

    @staticmethod
    def _env_skip_intent_llm() -> bool:
        return os.environ.get("XCAGI_SKIP_INTENT_LLM", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }

    def _should_use_rule_only_intent(self, request_context: dict[str, Any] | None) -> bool:
        if self._env_skip_intent_llm():
            return True
        return isinstance(request_context, dict) and bool(request_context.get("skip_intent_llm"))

    def _intent_rule_only_fast(self, message: str) -> dict[str, Any]:
        r = self.intent_service(message)
        if not isinstance(r, dict):
            r = {}
        return {
            "primary_intent": r.get("primary_intent"),
            "final_intent": r.get("primary_intent") or r.get("tool_key"),
            "tool_key": r.get("tool_key"),
            "intent_hints": list(r.get("intent_hints") or []),
            "is_negated": bool(r.get("is_negated")),
            "is_greeting": bool(r.get("is_greeting")),
            "is_goodbye": bool(r.get("is_goodbye")),
            "is_help": bool(r.get("is_help")),
            "is_confirmation": bool(r.get("is_confirmation")),
            "is_negation_intent": bool(r.get("is_negation_intent")),
            "is_likely_unclear": bool(r.get("is_likely_unclear")),
            "slots": {},
            "all_matched_tools": r.get("all_matched_tools", []),
            "intent_source": "rule_only_fast",
        }

    def _neuro_stack_enabled(self) -> bool:
        from app.neuro_bus.integrations.intent_integration import is_neuro_stack_enabled

        return is_neuro_stack_enabled()

    def _convert_neuro_intent_bridge(self, nr: Any) -> dict[str, Any]:
        from app.domain.neuro.reflex_arc import ReflexResult, ReflexType
        from app.neuro_bus.integrations.intent_integration import reflex_match_to_chat_intent_dict

        if getattr(nr, "recognizer_result", None) is not None:
            d = self._convert_recognizer_result(nr.recognizer_result)
            d["intent_source"] = "neuro_unified"
            return d
        if getattr(nr, "reflex_used", False):
            try:
                rt = ReflexType(nr.intent)
            except ValueError:
                rt = ReflexType.UNKNOWN
            rr = ReflexResult(
                True,
                rt,
                float(nr.confidence),
                str((nr.entities or {}).get("response", "")),
                0.0,
            )
            return reflex_match_to_chat_intent_dict(rr)
        return {
            "primary_intent": getattr(nr, "intent", None),
            "final_intent": getattr(nr, "intent", None),
            "tool_key": None,
            "intent_hints": [],
            "is_negated": False,
            "is_greeting": False,
            "is_goodbye": False,
            "is_help": False,
            "is_confirmation": False,
            "is_negation_intent": False,
            "is_likely_unclear": True,
            "slots": dict(nr.entities or {}),
            "all_matched_tools": [],
            "intent_source": "neuro_fallback",
        }

    async def _recognize_intent(
        self,
        message: str,
        source: str | None,
        user_id: str,
        request_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ai_mode = self._resolve_ai_mode(user_id)
        is_offline_mode = ai_mode == "offline"

        if self._neuro_stack_enabled() and not self._is_pro_source(source):
            from app.neuro_bus.integrations.intent_integration import try_neuro_reflex_intent

            reflex_early = try_neuro_reflex_intent(message, user_id)
            if reflex_early is not None:
                reflex_early["ai_mode"] = ai_mode
                logger.info("[INTENT] neuro_reflex 快速命中（非 pro 路径）")
                try:
                    from app.neuro_bus.application_neuro_bridge import neuro_notify_intent_resolved

                    neuro_notify_intent_resolved(user_id, reflex_early)
                except Exception:
                    logger.debug("neuro_notify_intent_resolved skipped", exc_info=True)
                return reflex_early

        if is_offline_mode:
            logger.info("[INTENT] 离线模式：使用本地蒸馏规则识别")
            intent_result = await self.offline_intent_service.recognize(message)
        elif self._is_pro_source(source):
            if self._neuro_stack_enabled():
                from app.neuro_bus.integrations.intent_integration import (
                    get_neuro_intent_recognizer,
                )

                logger.info("[INTENT] 使用 neuro + unified_recognizer (pro mode)")
                neuro_r = get_neuro_intent_recognizer().recognize(
                    message,
                    user_id,
                    context=None,
                    context_data=request_context,
                )
                intent_result = self._convert_neuro_intent_bridge(neuro_r)
            else:
                logger.info("[INTENT] 使用 unified_recognizer (pro mode)")
                recognizer_result = self.unified_recognizer.recognize(
                    message,
                    context=None,
                    context_data=request_context,
                )
                intent_result = self._convert_recognizer_result(recognizer_result)
        elif self._should_use_rule_only_intent(request_context):
            logger.info(
                "[INTENT] rule_only_fast（跳过意图 DeepSeek，仅规则；可设 XCAGI_SKIP_INTENT_LLM=1 或 context.skip_intent_llm）"
            )
            intent_result = self._intent_rule_only_fast(message)
        else:
            logger.info("[INTENT] 使用 deepseek_intent_service (普通模式)")
            intent_result = await self.online_intent_service.recognize(message)

        intent_result["ai_mode"] = ai_mode
        try:
            from app.neuro_bus.application_neuro_bridge import neuro_notify_intent_resolved

            neuro_notify_intent_resolved(user_id, intent_result)
        except Exception:
            logger.debug("neuro_notify_intent_resolved skipped", exc_info=True)
        return intent_result

    def _convert_recognizer_result(self, recognizer_result) -> dict[str, Any]:
        return {
            "primary_intent": recognizer_result.primary_intent,
            "final_intent": recognizer_result.primary_intent,
            "tool_key": recognizer_result.tool_key,
            "intent_hints": recognizer_result.intent_hints,
            "is_negated": recognizer_result.is_negated,
            "is_greeting": recognizer_result.is_greeting,
            "is_goodbye": recognizer_result.is_goodbye,
            "is_help": recognizer_result.is_help,
            "is_confirmation": recognizer_result.is_confirmation,
            "is_negation_intent": recognizer_result.is_negation_intent,
            "is_likely_unclear": recognizer_result.is_likely_unclear,
            "slots": recognizer_result.slots,
            "all_matched_tools": recognizer_result.all_matched_tools,
            "intent_source": "unified_recognizer",
        }

    def _enhance_intent_slots(
        self, message: str, intent_result: dict[str, Any], user_id: str
    ) -> dict[str, Any]:
        intent_result = self._enhance_with_task_agent(message, intent_result, user_id)
        intent_result = self._enhance_with_shipment_parser(message, intent_result)
        return intent_result

    def _enhance_with_task_agent(
        self, message: str, intent_result: dict[str, Any], user_id: str
    ) -> dict[str, Any]:
        plan = self.task_agent.parse_task(message, {"user_id": user_id})
        if not plan or not isinstance(plan, dict):
            return intent_result

        task_type = plan.get("task_type")
        task_slots = plan.get("slots") or {}
        task_to_tool = {
            "shipment_generate": "shipment_generate",
            "product_query": "products",
            "customer_query": "customers",
            "print_config": "system",
            "customer_supplement": "customers",
        }

        if task_type not in task_to_tool:
            return intent_result

        merged_slots = {}
        merged_slots.update(intent_result.get("slots") or {})
        merged_slots.update(task_slots)
        intent_result["slots"] = merged_slots

        if not intent_result.get("tool_key"):
            intent_result["tool_key"] = task_to_tool[task_type]
        if not intent_result.get("final_intent"):
            intent_result["final_intent"] = task_type
        if not intent_result.get("primary_intent"):
            intent_result["primary_intent"] = task_type

        return intent_result

    def _enhance_with_shipment_parser(
        self, message: str, intent_result: dict[str, Any]
    ) -> dict[str, Any]:
        final_intent_name = intent_result.get("final_intent") or intent_result.get("primary_intent")
        if final_intent_name != "shipment_generate":
            return intent_result

        merged_slots = dict(intent_result.get("slots") or {})
        try:
            from app.routes.tools import _parse_order_text

            parsed_order = _parse_order_text(message)
            if not parsed_order.get("success"):
                return intent_result

            products = parsed_order.get("products") or []
            first = products[0] if products else {}

            if products:
                merged_slots["products"] = products
            if parsed_order.get("unit_name"):
                merged_slots["unit_name"] = parsed_order.get("unit_name")

            if not (
                merged_slots.get("model_number") or merged_slots.get("product_model")
            ) and first.get("model_number"):
                merged_slots["model_number"] = first.get("model_number")
            if not merged_slots.get("tin_spec") and first.get("tin_spec"):
                merged_slots["tin_spec"] = first.get("tin_spec")
            if not merged_slots.get("quantity_tins") and first.get("quantity_tins"):
                merged_slots["quantity_tins"] = first.get("quantity_tins")

            intent_result["slots"] = merged_slots
        except Exception:
            logger.debug("suppressed exception", exc_info=True)

        return intent_result
