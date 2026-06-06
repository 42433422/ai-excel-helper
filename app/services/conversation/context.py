import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConversationContext:

    user_id: str
    conversation_history: list[dict[str, str]] = field(default_factory=list)
    current_file: str | None = None
    last_action: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    current_intent: str | None = None
    current_tool_key: str | None = None
    intent_hints: list[str] = field(default_factory=list)
    pending_confirmation: dict[str, Any] | None = None
    last_intent_result: dict[str, Any] | None = None


class ContextMixin:

    def get_context(self, user_id: str) -> ConversationContext | None:
        return self.contexts.get(user_id)

    def create_context(self, user_id: str) -> ConversationContext:
        context = ConversationContext(user_id=user_id)
        self.contexts[user_id] = context
        logger.info(f"为用户 {user_id} 创建新的对话上下文")
        return context

    def update_context(self, user_id: str, **kwargs) -> ConversationContext | None:
        context = self.contexts.get(user_id)
        if not context:
            return None

        for key, value in kwargs.items():
            if hasattr(context, key):
                setattr(context, key, value)

        context.updated_at = time.time()
        return context

    def set_pending_confirmation(self, user_id: str, confirmation_data: dict[str, Any]) -> bool:
        context = self.contexts.get(user_id)
        if not context:
            context = self.create_context(user_id)

        context.pending_confirmation = confirmation_data
        context.updated_at = time.time()
        return True

    def _get_or_create_context(
        self, user_id: str, context: dict[str, Any] | None
    ) -> ConversationContext:
        conv_context = self.get_context(user_id)
        if not conv_context:
            conv_context = self.create_context(user_id)
        enriched = self._enrich_context_with_kitten_business_snapshot(context)
        self._apply_request_context(conv_context, enriched)
        return conv_context

    async def _get_or_create_context_async(
        self,
        user_id: str,
        context: dict[str, Any] | None,
        message: str,
    ) -> ConversationContext:
        conv_context = self.get_context(user_id)
        if not conv_context:
            conv_context = self.create_context(user_id)
        enriched = self._enrich_context_with_kitten_business_snapshot(context)
        enriched = await self._enrich_kitten_web_search_if_needed(enriched, message, user_id)
        self._apply_request_context(conv_context, enriched)
        return conv_context

    def _update_context_from_intent(
        self, conv_context: ConversationContext, intent_result: dict[str, Any]
    ) -> None:
        conv_context.current_intent = intent_result.get("final_intent") or intent_result.get(
            "primary_intent"
        )
        conv_context.current_tool_key = intent_result.get("tool_key")
        conv_context.intent_hints = intent_result.get("intent_hints", [])
        conv_context.last_intent_result = intent_result

    def _enrich_context_with_kitten_business_snapshot(
        self, context: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        if not isinstance(context, dict):
            return context
        if not context.get("kitten_analyzer"):
            return context
        out = dict(context)
        if out.get("kitten_include_business_db"):
            try:
                from app.services.kitten_business_snapshot import (
                    build_kitten_business_snapshot,
                )

                out["kitten_business_snapshot"] = build_kitten_business_snapshot()
            except Exception as exc:
                logger.warning("kitten business snapshot build failed: %s", exc)
                out["kitten_business_snapshot"] = {
                    "success": False,
                    "text": f"【业务数据库快照】生成失败：{exc}",
                    "stats": {},
                }
        else:
            out.pop("kitten_business_snapshot", None)
        return out

    async def _enrich_kitten_web_search_if_needed(
        self,
        context: dict[str, Any] | None,
        message: str,
        user_id: str,
    ) -> dict[str, Any] | None:
        if not isinstance(context, dict):
            return context
        if not context.get("kitten_analyzer") or not context.get("kitten_web_search"):
            return context
        try:
            from app.infrastructure.web_search import kitten_web_search

            result = await kitten_web_search(message.strip(), user_key=user_id or "anonymous")
        except Exception as exc:
            logger.warning("kitten web search: %s", exc)
            out = dict(context)
            out["web_search_results"] = []
            out["web_search_error"] = str(exc)
            return out
        out = dict(context)
        out["web_search_results"] = result.get("hits") if result.get("success") else []
        if not result.get("success"):
            out["web_search_error"] = result.get("message") or "search failed"
        else:
            out.pop("web_search_error", None)
        out["web_search_meta"] = {
            "provider": result.get("provider"),
            "query": result.get("query"),
        }
        return out

    def _apply_request_context(
        self,
        conv_context: ConversationContext,
        ctx: dict[str, Any] | None,
    ) -> None:
        if ctx is None:
            return
        if not ctx:
            return
        prev = (conv_context.metadata or {}).get("request_context") or {}
        merged: dict[str, Any] = {**prev, **ctx}
        if ctx.get("kitten_analyzer") and ctx.get("has_dataset") is False:
            merged.pop("kitten_dataset", None)
        elif "kitten_dataset" in ctx:
            if ctx["kitten_dataset"]:
                merged["kitten_dataset"] = self._sanitize_kitten_dataset(ctx["kitten_dataset"])
            else:
                merged.pop("kitten_dataset", None)
        elif prev.get("kitten_dataset"):
            merged["kitten_dataset"] = prev["kitten_dataset"]

        if ctx.get("kitten_analyzer"):
            if ctx.get("kitten_include_business_db") and ctx.get("kitten_business_snapshot"):
                merged["kitten_business_snapshot"] = self._sanitize_kitten_business_snapshot(
                    ctx["kitten_business_snapshot"]
                )
            else:
                merged.pop("kitten_business_snapshot", None)
            if not ctx.get("kitten_web_search"):
                merged.pop("web_search_results", None)
                merged.pop("web_search_error", None)
                merged.pop("web_search_meta", None)
            if "web_search_results" in ctx:
                merged["web_search_results"] = self._sanitize_web_search_results(
                    ctx.get("web_search_results")
                )
            if ctx.get("web_search_error"):
                merged["web_search_error"] = str(ctx.get("web_search_error"))[:500]
            elif "web_search_error" in merged:
                merged.pop("web_search_error", None)
            meta = ctx.get("web_search_meta")
            if isinstance(meta, dict) and meta:
                merged["web_search_meta"] = {
                    k: str(v)[:200] for k, v in meta.items() if v is not None
                }
            elif "web_search_meta" in merged:
                merged.pop("web_search_meta", None)
        conv_context.metadata.setdefault("request_context", {})
        conv_context.metadata["request_context"] = merged
        conv_context.updated_at = time.time()

    def clear_context(self, user_id: str) -> bool:
        if user_id in self.contexts:
            del self.contexts[user_id]
            logger.info(f"已清除用户 {user_id} 的对话上下文")
            return True
        return False

    def get_all_contexts(self) -> dict[str, ConversationContext]:
        return self.contexts.copy()

    def cleanup_old_contexts(self, max_age_seconds: int = 3600) -> int:
        current_time = time.time()
        to_remove = []

        for user_id, context in self.contexts.items():
            if current_time - context.updated_at > max_age_seconds:
                to_remove.append(user_id)

        for user_id in to_remove:
            del self.contexts[user_id]

        if to_remove:
            logger.info(f"清理了 {len(to_remove)} 个过期的对话上下文")

        return len(to_remove)
