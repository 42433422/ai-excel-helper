from __future__ import annotations
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.application.excel_vector_app_service import HashEmbedder
from app.application.ports.vector_store import VectorStorePort
from app.infrastructure.persistence.user_memory_vector_store import get_user_memory_vector_store


@dataclass
class UserMemoryVectorChunk:
    chunk_id: str
    content: str
    metadata: Dict[str, Any]


class UserMemoryVectorIngestApplicationService:
    """把用户记忆事件（action/feedback 等）写入用户向量库。"""

    def __init__(
        self,
        vector_store: Optional[VectorStorePort] = None,
        embedder: Optional[HashEmbedder] = None,
    ) -> None:
        self._vector_store = vector_store or get_user_memory_vector_store()
        self._embedder = embedder or HashEmbedder()

    def _ensure_user_index(self, user_id: str) -> None:
        if hasattr(self._vector_store, "create_or_update_index"):
            # index_id 直接映射为 user_id，便于 RAG 查询只传 user_id。
            getattr(self._vector_store, "create_or_update_index")(index_id=user_id, user_id=user_id)

    def ingest_chunks(
        self,
        user_id: str,
        chunks: List[UserMemoryVectorChunk],
    ) -> Dict[str, Any]:
        if not user_id:
            return {"success": False, "message": "缺少 user_id"}
        if not chunks:
            return {"success": True, "message": "无可写入内容", "written": 0}

        self._ensure_user_index(user_id)

        texts = [c.content for c in chunks]
        embeddings = self._embedder.embed_texts(texts)
        store_payload: List[Dict[str, Any]] = []
        for c, emb in zip(chunks, embeddings):
            store_payload.append(
                {
                    "chunk_id": c.chunk_id,
                    "content": c.content,
                    "embedding": emb,
                    "metadata": c.metadata,
                }
            )

        written = self._vector_store.upsert_chunks(index_id=user_id, chunks=store_payload)
        return {"success": True, "index_id": user_id, "written": written, "chunk_count": written}

    def build_action_chunk(self, user_id: str, intent: str, slots: Dict[str, Any], message: str) -> UserMemoryVectorChunk:
        ts = datetime.now().isoformat()
        # content 既用于 embedding 也用于“调试可读”，尽量包含关键槽位与意图。
        slot_brief: Dict[str, Any] = {}
        for k in ("unit_name", "product_name", "model_number", "tin_spec", "quantity_tins", "keyword", "customer_name", "unit_price"):
            if k in (slots or {}) and (slots or {}).get(k) not in (None, ""):
                slot_brief[k] = (slots or {}).get(k)
        content = (
            f"[user_action] intent={intent}; "
            f"slots={slot_brief}; "
            f"message={str(message or '').strip()[:120]}"
        )
        return UserMemoryVectorChunk(
            chunk_id=uuid.uuid4().hex,
            content=content,
            metadata={
                "source": "action",
                "intent": intent,
                "slots": slot_brief,
                "last_used": ts,
                "message_preview": str(message or '').strip()[:200],
                "ts": ts,
                "user_id": user_id,
            },
        )

    def build_feedback_chunk(
        self,
        user_id: str,
        message: str,
        recognized_intent: str,
        feedback: str,
        corrected_intent: Optional[str],
        slots: Optional[Dict[str, Any]] = None,
    ) -> UserMemoryVectorChunk:
        ts = datetime.now().isoformat()
        slot_brief: Dict[str, Any] = {}
        slots = slots or {}
        for k in ("unit_name", "product_name", "model_number", "tin_spec", "quantity_tins", "keyword", "customer_name", "field_name", "field_value"):
            if k in slots and slots.get(k) not in (None, ""):
                slot_brief[k] = slots.get(k)

        content = (
            "[user_feedback] "
            f"recognized_intent={recognized_intent}; feedback={feedback}; "
            f"corrected_intent={corrected_intent or ''}; "
            f"slots={slot_brief}; "
            f"message={str(message or '').strip()[:120]}"
        )
        return UserMemoryVectorChunk(
            chunk_id=uuid.uuid4().hex,
            content=content,
            metadata={
                "source": "feedback",
                "recognized_intent": recognized_intent,
                "user_feedback": feedback,
                "corrected_intent": corrected_intent,
                "slots": slot_brief,
                "last_used": ts,
                "message_preview": str(message or '').strip()[:200],
                "ts": ts,
                "user_id": user_id,
            },
        )


class UserMemoryRagApplicationService:
    """用户记忆 RAG：基于用户向量库做语义检索。"""

    def __init__(
        self,
        vector_store: Optional[VectorStorePort] = None,
        embedder: Optional[HashEmbedder] = None,
    ) -> None:
        self._vector_store = vector_store or get_user_memory_vector_store()
        self._embedder = embedder or HashEmbedder()

    def query(self, user_id: str, query_text: str, top_k: int = 5) -> Dict[str, Any]:
        if not user_id:
            return {"success": False, "message": "缺少 user_id"}
        query_text = str(query_text or "").strip()
        if not query_text:
            return {"success": False, "message": "缺少 query_text"}

        query_vector = self._embedder.embed_query(query_text)
        hits = self._vector_store.query(index_id=user_id, query_vector=query_vector, top_k=top_k)
        return {"success": True, "user_id": user_id, "query": query_text, "top_k": top_k, "hits": hits}

    def format_for_prompt(self, user_id: str, query_text: str, hits: List[Dict[str, Any]], max_hits: int = 6) -> str:
        if not hits:
            return "【UserMemoryRAG】未召回用户记忆片段。"

        lines: List[str] = ["【UserMemoryRAG】召回到以下用户记忆片段（用于辅助决策）:"]
        for idx, hit in enumerate(hits[:max_hits], start=1):
            score = float(hit.get("score") or 0.0)
            md = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
            source = str(md.get("source") or "-")
            intent = md.get("intent") or md.get("recognized_intent") or ""
            user_feedback = md.get("user_feedback") or ""
            corrected_intent = md.get("corrected_intent") or ""
            last_used = md.get("last_used") or ""
            slots = md.get("slots") if isinstance(md.get("slots"), dict) else {}

            # slots 可能含较多键，做轻量展示。
            slot_str = ", ".join([f"{k}={slots[k]}" for k in list(slots.keys())[:6]])
            preview = str(hit.get("content") or "").strip()
            if len(preview) > 240:
                preview = preview[:240] + "…"

            lines.append(
                f"{idx}. source={source}; intent={intent}; feedback={user_feedback or '-'}; corrected_intent={corrected_intent or '-'}; "
                f"last_used={last_used or '-'}; slots({slot_str or '-'}) ; score={score:.4f}\n"
                f"   content={preview}"
            )
        lines.append("优先参考以上片段的意图/习惯（不要编造片段中不存在的信息）。")
        return "\n".join(lines)


_user_memory_vector_ingest_service: Optional[UserMemoryVectorIngestApplicationService] = None
_user_memory_rag_service: Optional[UserMemoryRagApplicationService] = None


def get_user_memory_vector_ingest_app_service() -> UserMemoryVectorIngestApplicationService:
    global _user_memory_vector_ingest_service
    if _user_memory_vector_ingest_service is None:
        _user_memory_vector_ingest_service = UserMemoryVectorIngestApplicationService()
    return _user_memory_vector_ingest_service


def get_user_memory_rag_app_service() -> UserMemoryRagApplicationService:
    global _user_memory_rag_service
    if _user_memory_rag_service is None:
        _user_memory_rag_service = UserMemoryRagApplicationService()
    return _user_memory_rag_service

