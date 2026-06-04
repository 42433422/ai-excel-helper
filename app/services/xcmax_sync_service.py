"""XCmax 双向同步服务。

对外提供:
  record_change(entity_type, entity_id, operation, payload) — 记录变更并入 outbox
  push_outbox(remote_host, remote_port)  — 把本地 outbox 推送到远端
  pull_from_remote(remote_host, remote_port, since_cursor)  — 从远端拉取增量变更
  apply_inbox()  — 把 inbox 中的变更应用到本地业务数据库

支持的实体类型（entity_type）：
  personnel      人员档案
  department     部门
  attendance     考勤记录（shipment_records）
  approval       审批请求
  approval_flow  审批流程定义
  print_job      打印任务
  template       文档/打印模板
  model_config   模型服务配置
  ecosystem      智能生态配置
  workflow_employee  员工工作流节点
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

_NODE_ID = os.environ.get("XCMAX_NODE_ID", "local")


# ---------------------------------------------------------------------------
# 公共变更记录入口（各业务路由均可调用）
# ---------------------------------------------------------------------------


def record_change(
    entity_type: str,
    entity_id: str,
    operation: str,
    payload: dict[str, Any],
    *,
    actor: str = "system",
    version: int = 1,
) -> int:
    """记录变更并自动写入 outbox，供各业务路由调用（非阻塞，失败不影响主流程）。

    使用示例（在 FastAPI 路由中）：
        from app.services.xcmax_sync_service import record_change
        record_change("attendance", str(record_id), "insert", {"employee": "张三", ...})
    """
    try:
        from app.db.xcmax_sync import SyncDb

        db = SyncDb()
        return db.append_change(
            entity_type=entity_type,
            entity_id=str(entity_id),
            operation=operation,
            payload=payload,
            version=version,
            actor=actor,
            origin_node=_NODE_ID,
            enqueue_outbox=True,
        )
    except Exception as exc:
        logger.warning("record_change failed (entity=%s id=%s): %s", entity_type, entity_id, exc)
        return -1


# ---------------------------------------------------------------------------
# 推送 outbox → 远端
# ---------------------------------------------------------------------------


def push_outbox(
    remote_host: str | None = None,
    remote_port: int | None = None,
) -> dict[str, Any]:
    """读取 pending outbox 条目，逐条 POST 到远端 /api/xcmax/sync/receive。"""
    from app.db.xcmax_sync import SyncDb

    host = remote_host or os.environ.get("XCMAX_REMOTE_HOST", "119.27.178.147")
    port = int(remote_port or os.environ.get("XCMAX_REMOTE_PORT", "9999"))
    base_url = f"http://{host}:{port}"

    db = SyncDb()
    pending = db.get_pending_outbox(limit=200)
    sent = failed = 0

    for item in pending:
        outbox_id = item["id"]
        payload = {
            "entity_type": item["entity_type"],
            "entity_id": item["entity_id"],
            "operation": item["operation"],
            "payload": item.get("payload") or {},
            "origin_node": _NODE_ID,
        }
        try:
            body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
            req = urllib.request.Request(
                f"{base_url}/api/xcmax/sync/receive",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read(4096)
            db.mark_outbox_sent(outbox_id)
            sent += 1
        except urllib.error.HTTPError as exc:
            err_msg = f"HTTP {exc.code}: {exc.reason}"
            logger.warning("outbox push item %s failed: %s", outbox_id, err_msg)
            db.mark_outbox_failed(outbox_id, err_msg, retry=exc.code >= 500)
            failed += 1
        except Exception as exc:
            err_msg = str(exc)
            logger.warning("outbox push item %s failed: %s", outbox_id, err_msg)
            db.mark_outbox_failed(outbox_id, err_msg, retry=True)
            failed += 1

    return {"sent": sent, "failed": failed, "total_pending": len(pending)}


# ---------------------------------------------------------------------------
# 拉取远端变更 → inbox
# ---------------------------------------------------------------------------


def pull_from_remote(
    remote_host: str | None = None,
    remote_port: int | None = None,
    since_cursor: int | None = None,
) -> dict[str, Any]:
    """从远端拉取增量变更写入 inbox。"""
    from app.db.xcmax_sync import SyncDb

    host = remote_host or os.environ.get("XCMAX_REMOTE_HOST", "119.27.178.147")
    port = int(remote_port or os.environ.get("XCMAX_REMOTE_PORT", "9999"))

    db = SyncDb()
    status = db.get_status()
    cursor = since_cursor if since_cursor is not None else (status.get("remote_cursor") or 0)

    url = f"http://{host}:{port}/api/xcmax/sync/changes?since_cursor={cursor}&limit=200"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read(1024 * 512).decode("utf-8", errors="replace"))
        changes = body.get("data") or []
        if changes:
            db.enqueue_inbox(changes, remote_cursor=int(changes[-1].get("id") or 0))
            db.update_remote_cursor(int(changes[-1].get("id") or 0))
        return {"pulled": len(changes), "since_cursor": cursor}
    except Exception as exc:
        logger.warning("pull_from_remote failed: %s", exc)
        return {"pulled": 0, "error": str(exc)}


# ---------------------------------------------------------------------------
# 应用 inbox → 本地业务库
# ---------------------------------------------------------------------------

_ENTITY_APPLIERS: dict[str, Any] = {}


def register_entity_applier(entity_type: str):
    """装饰器：注册业务实体变更应用函数。"""

    def decorator(fn):
        _ENTITY_APPLIERS[entity_type] = fn
        return fn

    return decorator


@register_entity_applier("personnel")
def _apply_personnel(item: dict[str, Any]) -> None:
    """人员变更：写入 taiyangniao-pro attendance_employees / products。"""
    payload = item.get("payload") or {}
    name = str(payload.get("name") or payload.get("employee_name") or "").strip()
    if not name:
        return
    try:
        from app.mod_sdk.private_sqlite import resolve_mod_private_sqlite_path
        import sqlite3
        from datetime import datetime

        db_path = resolve_mod_private_sqlite_path("taiyangniao_pro.db")
        conn = sqlite3.connect(str(db_path))
        now = datetime.now().isoformat(timespec="seconds")
        dept = str(payload.get("department") or "").strip()
        conn.execute(
            """
            INSERT OR IGNORE INTO attendance_employees
                (source_file, employee_name, department, main_department,
                 attendance_group, employee_no, position, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "xcmax_sync",
                name,
                dept,
                dept,
                payload.get("attendance_group") or "XCmax",
                payload.get("employee_no") or "",
                payload.get("position") or "",
                payload.get("user_id") or "",
            ),
        )
        conn.execute(
            """
            INSERT INTO products (source_file, model_number, name, specification, price, unit, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "xcmax_sync",
                payload.get("employee_id") or name,
                name,
                payload.get("position") or "",
                0.0,
                dept,
                now,
                now,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("apply_personnel failed for %s: %s", name, exc)


@register_entity_applier("department")
def _apply_department(item: dict[str, Any]) -> None:
    """部门变更：写入 attendance_departments / customers。"""
    payload = item.get("payload") or {}
    dept = str(payload.get("department") or payload.get("customer_name") or "").strip()
    if not dept:
        return
    try:
        from app.mod_sdk.private_sqlite import resolve_mod_private_sqlite_path
        import sqlite3
        from datetime import datetime

        db_path = resolve_mod_private_sqlite_path("taiyangniao_pro.db")
        conn = sqlite3.connect(str(db_path))
        now = datetime.now().isoformat(timespec="seconds")
        conn.execute(
            """
            INSERT OR IGNORE INTO attendance_departments
                (source_file, department, main_department, attendance_group)
            VALUES (?, ?, ?, ?)
            """,
            ("xcmax_sync", dept, dept, payload.get("attendance_group") or "XCmax"),
        )
        conn.execute(
            """
            INSERT INTO customers (source_file, customer_name, contact_person, contact_phone,
                                   address, purchase_unit, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("xcmax_sync", dept, "", "", "", "", now, now),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.warning("apply_department failed for %s: %s", dept, exc)


@register_entity_applier("attendance")
def _apply_attendance(item: dict[str, Any]) -> None:
    """考勤记录变更：写入主库 shipment_records 表（考勤行业语义）。"""
    payload = item.get("payload") or {}
    operation = item.get("operation", "sync")
    try:
        from app.db import get_db
        from app.db.models.shipment import ShipmentRecord
        from datetime import datetime as _dt

        with get_db() as db:
            record_id = payload.get("id")
            if operation == "delete" and record_id:
                obj = db.query(ShipmentRecord).filter(ShipmentRecord.id == record_id).first()
                if obj:
                    db.delete(obj)
                    db.commit()
                return

            purchase_unit = str(
                payload.get("purchase_unit") or payload.get("employee_name") or ""
            ).strip()
            product_name = str(
                payload.get("product_name") or payload.get("attendance_group") or ""
            ).strip()
            if not purchase_unit or not product_name:
                return

            if record_id:
                obj = db.query(ShipmentRecord).filter(ShipmentRecord.id == record_id).first()
            else:
                obj = None

            if obj:
                for col in ("purchase_unit", "product_name", "model_number", "status", "raw_text"):
                    if col in payload:
                        setattr(obj, col, payload[col])
                obj.updated_at = _dt.now()
            else:
                obj = ShipmentRecord(
                    purchase_unit=purchase_unit,
                    product_name=product_name,
                    model_number=str(payload.get("model_number") or ""),
                    quantity_kg=float(payload.get("quantity_kg") or 0),
                    quantity_tins=int(payload.get("quantity_tins") or 0),
                    status=str(payload.get("status") or "pending"),
                    created_at=_dt.now(),
                    updated_at=_dt.now(),
                )
                db.add(obj)
            db.commit()
    except Exception as exc:
        logger.warning("apply_attendance failed: %s", exc)


@register_entity_applier("approval")
def _apply_approval(item: dict[str, Any]) -> None:
    """审批请求变更：更新 approval_requests 表的状态字段。"""
    payload = item.get("payload") or {}
    operation = item.get("operation", "sync")
    try:
        from app.db import get_db
        from app.db.models.approval import ApprovalRequest
        from datetime import datetime as _dt

        with get_db() as db:
            record_id = payload.get("id")
            if not record_id:
                return
            obj = db.query(ApprovalRequest).filter(ApprovalRequest.id == record_id).first()
            if not obj:
                return
            if operation == "delete":
                db.delete(obj)
            else:
                for col in ("status", "title", "description", "priority", "applicant_name"):
                    if col in payload:
                        setattr(obj, col, payload[col])
                obj.updated_at = _dt.now()
            db.commit()
    except Exception as exc:
        logger.warning("apply_approval failed: %s", exc)


@register_entity_applier("approval_flow")
def _apply_approval_flow(item: dict[str, Any]) -> None:
    """审批流程定义变更：同步 approval_flows 表的 is_active 和配置字段。"""
    payload = item.get("payload") or {}
    try:
        from app.db import get_db
        from app.db.models.approval import ApprovalFlow
        from datetime import datetime as _dt

        with get_db() as db:
            flow_key = str(payload.get("flow_key") or "").strip()
            if not flow_key:
                return
            obj = db.query(ApprovalFlow).filter(ApprovalFlow.flow_key == flow_key).first()
            if obj:
                for col in ("flow_name", "description", "is_active", "timeout_hours"):
                    if col in payload:
                        setattr(obj, col, payload[col])
                obj.updated_at = _dt.now()
                db.commit()
    except Exception as exc:
        logger.warning("apply_approval_flow failed: %s", exc)


@register_entity_applier("print_job")
def _apply_print_job(item: dict[str, Any]) -> None:
    """打印任务变更：写入打印作业日志表（若存在），否则记录结构化日志。"""
    payload = item.get("payload") or {}
    operation = item.get("operation", "sync")
    try:
        from app.db import get_db

        # 尝试写入打印作业表，若无此表则降级记录结构化日志
        with get_db() as db:
            from sqlalchemy import text

            db.execute(
                text(
                    """
                INSERT INTO print_jobs (entity_id, template, status, payload_json, created_at)
                VALUES (:eid, :tpl, :status, :payload, NOW())
                ON CONFLICT (entity_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    payload_json = EXCLUDED.payload_json
            """
                ),
                {
                    "eid": item.get("entity_id") or "",
                    "tpl": str(payload.get("template") or ""),
                    "status": str(payload.get("status") or operation),
                    "payload": json.dumps(payload, ensure_ascii=False, default=str),
                },
            )
            db.commit()
    except Exception:
        # 降级：仅写结构化日志
        logger.info(
            "print_job sync [%s] entity=%s status=%s",
            operation,
            item.get("entity_id"),
            payload.get("status"),
        )


@register_entity_applier("template")
def _apply_template(item: dict[str, Any]) -> None:
    """文档/打印模板变更：更新 document_templates 表或本地模板文件路径记录。"""
    payload = item.get("payload") or {}
    operation = item.get("operation", "sync")
    try:
        from app.db import get_db
        from sqlalchemy import text

        template_id = str(payload.get("template_id") or item.get("entity_id") or "").strip()
        if not template_id:
            return
        with get_db() as db:
            if operation == "delete":
                db.execute(
                    text("DELETE FROM document_templates WHERE slug = :s"), {"s": template_id}
                )
            else:
                db.execute(
                    text(
                        """
                    INSERT INTO document_templates (slug, name, category, is_active, created_at)
                    VALUES (:slug, :name, :cat, true, NOW())
                    ON CONFLICT (slug) DO UPDATE SET
                        name = EXCLUDED.name,
                        category = EXCLUDED.category
                """
                    ),
                    {
                        "slug": template_id,
                        "name": str(payload.get("name") or template_id),
                        "cat": str(payload.get("category") or "word"),
                    },
                )
            db.commit()
    except Exception as exc:
        logger.debug("apply_template non-fatal: %s", exc)


@register_entity_applier("model_config")
def _apply_model_config(item: dict[str, Any]) -> None:
    """模型服务配置变更：更新用户默认 LLM 配置（写入 users.default_llm_json）。"""
    payload = item.get("payload") or {}
    try:
        from app.db import get_db
        from app.db.models.user import User

        with get_db() as db:
            user_id = payload.get("user_id")
            if not user_id:
                return
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                user.default_llm_json = json.dumps(
                    payload.get("llm_config") or {}, ensure_ascii=False
                )
                db.commit()
    except Exception as exc:
        logger.warning("apply_model_config failed: %s", exc)


@register_entity_applier("ecosystem")
def _apply_ecosystem(item: dict[str, Any]) -> None:
    """智能生态配置变更：记录生态组件启停状态（写入 sync_meta 供前端查询）。"""
    payload = item.get("payload") or {}
    try:
        from app.db.xcmax_sync import SyncDb, _resolve_db_path
        import sqlite3 as _sqlite3

        conn = _sqlite3.connect(str(_resolve_db_path()))
        key = f"ecosystem:{item.get('entity_id','default')}"
        conn.execute(
            "INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
            (key, json.dumps(payload, ensure_ascii=False, default=str)),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.debug("apply_ecosystem non-fatal: %s", exc)


@register_entity_applier("workflow_employee")
def _apply_workflow_employee(item: dict[str, Any]) -> None:
    """员工工作流节点变更：更新本地 Mod manifest 的 workflow_employees 状态快照。"""
    payload = item.get("payload") or {}
    operation = item.get("operation", "sync")
    employee_id = str(payload.get("employee_id") or item.get("entity_id") or "").strip()
    if not employee_id:
        return
    try:
        from app.db.xcmax_sync import _resolve_db_path
        import sqlite3 as _sqlite3

        conn = _sqlite3.connect(str(_resolve_db_path()))
        key = f"workflow_employee:{employee_id}"
        if operation == "delete":
            conn.execute("DELETE FROM sync_meta WHERE key=?", (key,))
        else:
            conn.execute(
                "INSERT OR REPLACE INTO sync_meta (key, value) VALUES (?, ?)",
                (key, json.dumps(payload, ensure_ascii=False, default=str)),
            )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.debug("apply_workflow_employee non-fatal: %s", exc)


def apply_inbox(limit: int = 200) -> dict[str, Any]:
    """幂等地把 inbox 中 pending 的变更应用到本地。"""
    from app.db.xcmax_sync import SyncDb
    import sqlite3

    db = SyncDb()
    try:
        db_path = db._resolve_db_path() if hasattr(db, "_resolve_db_path") else None
        from app.db.xcmax_sync import _resolve_db_path

        path = _resolve_db_path()
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT id, entity_type, entity_id, operation, payload_json FROM sync_inbox WHERE status='pending' LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
    except Exception as exc:
        logger.warning("apply_inbox read failed: %s", exc)
        return {"applied": 0, "errors": 1}

    applied = errors = conflicts = 0
    for row in rows:
        inbox_id = row["id"]
        entity_type = row["entity_type"]
        try:
            payload = json.loads(row["payload_json"] or "{}")
            item = {
                "entity_type": entity_type,
                "entity_id": row["entity_id"],
                "operation": row["operation"],
                "payload": payload,
            }
            applier = _ENTITY_APPLIERS.get(entity_type)
            if applier:
                applier(item)
                db.mark_inbox_applied(inbox_id)
                applied += 1
            else:
                logger.debug("no applier for entity_type=%s, skipping", entity_type)
                db.mark_inbox_applied(inbox_id)
                applied += 1
        except Exception as exc:
            db.mark_inbox_conflict(inbox_id, str(exc))
            conflicts += 1
            errors += 1

    return {"applied": applied, "conflicts": conflicts, "errors": errors}
