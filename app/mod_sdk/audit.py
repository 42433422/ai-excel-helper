"""
Mod SDK 审计工具 — 提供统一的审计写入接口给各 Mod blueprint。

Mod 在执行写操作（删除客户/产品、导出数据等）前调用 ``write_audit_event``，
审计记录落入主库 ``ai_action_audit`` 表，与审批模块共享同一张轨迹表。

用法示例（在 Mod blueprint.py 中）::

    from app.mod_sdk.audit import write_audit_event

    @bp.route('/customers/<int:cid>', methods=['DELETE'])
    def delete_customer(cid):
        write_audit_event(
            actor=request.headers.get('X-User-ID'),
            action='mod_customer_delete',
            payload={'customer_id': cid, 'mod_id': current_app.config.get('MOD_ID')},
        )
        ...
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def write_audit_event(
    actor: int | str | None,
    action: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """将一条审计记录写入 ``ai_action_audit``。

    失败时静默记录日志，不影响业务逻辑。
    """
    import json

    try:
        actor_id: int | None = None
        if actor is not None:
            try:
                actor_id = int(str(actor).strip())
            except (TypeError, ValueError):
                actor_id = None

        from sqlalchemy import text

        from app.db.session import get_db

        with get_db() as db:
            db.execute(
                text(
                    "INSERT INTO ai_action_audit (actor, action, payload) "
                    "VALUES (:actor, :action, :payload)"
                ),
                {
                    "actor": actor_id,
                    "action": str(action or "").strip()[:200],
                    "payload": json.dumps(payload or {}, ensure_ascii=False, default=str)[:4096],
                },
            )
    except Exception as e:
        logger.debug("audit write_event 失败（非致命）: %s", e)
