import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class PromptsMixin:

    def _sanitize_kitten_dataset(self, kd: Any) -> dict[str, Any]:
        if not isinstance(kd, dict):
            return {}
        out = dict(kd)
        pt = out.get("preview_text")
        if isinstance(pt, str) and len(pt) > 12000:
            out["preview_text"] = pt[:12000] + "\n…（已截断）"
        fields = (
            out.get("fields") if isinstance(out.get("fields"), list) else out.get("field_names")
        )
        if isinstance(fields, list) and len(fields) > 200:
            out["fields"] = [str(x) for x in fields[:200]]
            out["fields_truncated"] = True
        elif isinstance(fields, list):
            out["fields"] = [str(x) for x in fields]
        return out

    def _sanitize_kitten_business_snapshot(self, snap: Any) -> dict[str, Any]:
        if not isinstance(snap, dict):
            return {}
        out = dict(snap)
        pt = out.get("text")
        if isinstance(pt, str) and len(pt) > 14000:
            out["text"] = pt[:14000] + "\n…（已截断）"
        return out

    def _sanitize_web_search_results(self, hits: Any) -> list[dict[str, Any]]:
        if not isinstance(hits, list):
            return []
        out: list[dict[str, Any]] = []
        for item in hits[:8]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "")[:300]
            url = str(item.get("url") or "")[:500]
            snippet = str(item.get("snippet") or "")[:600]
            if url:
                out.append({"title": title, "url": url, "snippet": snippet})
        return out

    def _format_kitten_business_snapshot_block(self, snap: Any | None) -> str:
        if snap is None or (isinstance(snap, dict) and not snap):
            return ""
        if not isinstance(snap, dict):
            return ""
        preview = snap.get("text")
        if not isinstance(preview, str) or not preview.strip():
            return ""
        head = "【小猫分析· 业务数据库快照】"
        ga = snap.get("generated_at")
        if ga:
            head += f"（生成时间 {ga}）"
        return f"{head}\n{preview.strip()}"

    def _format_kitten_dataset_block(self, kd: Any | None) -> str:
        if kd is None or (isinstance(kd, dict) and not kd):
            return "【小猫分析】当前未附带表格数据，请根据通用数据分析知识回答用户问题。"
        if not isinstance(kd, dict):
            return ""
        lines = ["【小猫分析· 数据上下文】"]
        fn = kd.get("file_name") or kd.get("name")
        if fn:
            lines.append(f"文件名：{fn}")
        if kd.get("rows") is not None:
            lines.append(f"行数：{kd.get('rows')}")
        if kd.get("columns") is not None:
            lines.append(f"列数：{kd.get('columns')}")
        fields = kd.get("fields") or kd.get("field_names")
        if isinstance(fields, (list, tuple)) and fields:
            lines.append(f"字段：{', '.join(str(x) for x in fields[:80])}")
            if len(fields) > 80:
                lines.append("…（字段列表已省略）")
        preview = kd.get("preview_text")
        if isinstance(preview, str) and preview.strip():
            lines.append("样本行（供理解表格结构）：")
            lines.append(preview.strip())
        lines.append("（若字段名为 __EMPTY 等占位，请结合样本行推断含义。）")
        return "\n".join(lines)

    def _format_web_search_block(
        self,
        hits: Any,
        err: Any,
        meta: Any,
    ) -> str:
        lines: list[str] = ["【互联网检索摘要】"]
        if isinstance(meta, dict):
            prov = str(meta.get("provider") or "").strip()
            q = str(meta.get("query") or "").strip()
            if prov or q:
                lines.append(f"提供方：{prov or '-'}；检索查询：{q or '-'}")
        safe_hits = hits if isinstance(hits, list) else []
        if not safe_hits:
            if err:
                lines.append(f"本次未拿到网页摘要：{str(err)[:400]}")
            lines.append("请结合用户上传数据、业务库快照（若有）与自身知识回答；勿虚构检索结果。")
            return "\n".join(lines)
        lines.append("以下条目供引用（请在回答中标注来源序号或链接）：")
        for idx, item in enumerate(safe_hits[:8], start=1):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            snip = str(item.get("snippet") or "").strip()
            if len(snip) > 500:
                snip = snip[:500] + "…"
            lines.append(f"{idx}. {title or url}\n   {url}\n   {snip}")
        lines.append("严禁编造以上列表中不存在的链接或摘要；信息不足时请明确说明。")
        return "\n".join(lines)

    def _format_request_context_for_system(self, req: dict[str, Any] | None) -> str:
        if not req or not isinstance(req, dict):
            return ""
        blocks: list[str] = []
        if req.get("kitten_analyzer"):
            blocks.append(self._format_kitten_dataset_block(req.get("kitten_dataset")))
            db_block = self._format_kitten_business_snapshot_block(
                req.get("kitten_business_snapshot")
            )
            if db_block:
                blocks.append(db_block)
            if req.get("kitten_web_search"):
                blocks.append(
                    self._format_web_search_block(
                        req.get("web_search_results"),
                        req.get("web_search_error"),
                        req.get("web_search_meta"),
                    )
                )
        excel_vector_ctx = req.get("excel_vector_context")
        if isinstance(excel_vector_ctx, dict):
            blocks.append(self._format_excel_vector_block(excel_vector_ctx))
        extra = {
            k: v
            for k, v in req.items()
            if k
            not in (
                "kitten_analyzer",
                "has_dataset",
                "kitten_dataset",
                "kitten_include_business_db",
                "kitten_business_snapshot",
                "kitten_web_search",
                "web_search_results",
                "web_search_error",
                "web_search_meta",
                "excel_vector_context",
            )
        }
        if extra:
            try:
                dumped = json.dumps(extra, ensure_ascii=False, default=str)
                if len(dumped) > 4096:
                    dumped = dumped[:4096] + "…"
                blocks.append(f"【附加上下文】\n{dumped}")
            except Exception:
                logger.debug("suppressed exception", exc_info=True)
        merged = "\n\n".join(b for b in blocks if b)
        return merged

    def _format_excel_vector_block(self, payload: dict[str, Any]) -> str:
        index_id = str(payload.get("index_id") or "").strip()
        query = str(payload.get("query") or "").strip()
        hits = payload.get("hits") if isinstance(payload.get("hits"), list) else []
        lines = ["【Excel语义检索上下文】"]
        if index_id:
            lines.append(f"索引ID：{index_id}")
        if query:
            lines.append(f"问题：{query}")
        if not hits:
            lines.append("未召回相关内容。")
            lines.append("若信息不足，请明确告知用户并引导其补充筛选条件。")
            return "\n".join(lines)

        lines.append("以下是最相关的表格片段（按相关度排序）：")
        for idx, hit in enumerate(hits[:8], start=1):
            score = float(hit.get("score", 0.0))
            metadata = hit.get("metadata") if isinstance(hit.get("metadata"), dict) else {}
            sheet = str(metadata.get("sheet") or "-")
            row_index = metadata.get("row_index")
            content = str(hit.get("content") or "").strip()
            if len(content) > 600:
                content = content[:600] + "..."
            if row_index is not None:
                lines.append(f"{idx}. sheet={sheet}, row={row_index}, score={score:.4f}")
            else:
                lines.append(f"{idx}. sheet={sheet}, score={score:.4f}")
            lines.append(content)
        lines.append("回答时优先引用以上片段，不要编造未出现的数据。")
        return "\n".join(lines)

    def _metadata_cache_hash(self, metadata: dict[str, Any] | None) -> str:
        if not metadata:
            return ""
        try:
            return hashlib.md5(
                json.dumps(metadata, sort_keys=True, ensure_ascii=False, default=str).encode(
                    "utf-8"
                )
            ).hexdigest()
        except Exception:
            return str(hash(frozenset(metadata.keys())))

    def _build_context_prompt(self, context) -> str:
        blocks: list[str] = []
        req = (context.metadata or {}).get("request_context")
        req_block = self._format_request_context_for_system(req)
        if req_block:
            blocks.append(req_block)

        session_parts: list[str] = []
        if context.current_intent:
            session_parts.append(f"当前会话意图：{context.current_intent}")
        if context.current_tool_key:
            session_parts.append(f"当前工具：{context.current_tool_key}")
        if context.intent_hints:
            session_parts.append(f"意图线索：{', '.join(context.intent_hints)}")
        if context.pending_confirmation:
            action = context.pending_confirmation.get("action", "")
            desc = context.pending_confirmation.get("description", "")
            session_parts.append(f"待确认操作：{action} - {desc}")
        if context.last_action:
            session_parts.append(f"最近操作：{context.last_action}")
        if session_parts:
            blocks.append("【当前会话上下文】\n" + "\n".join(session_parts) + "\n【END会话上下文】")
        if not blocks:
            return ""
        return "\n\n".join(blocks)
