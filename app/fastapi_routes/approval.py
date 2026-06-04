"""
Approval workspace 前端兼容路由（FastAPI 原生）。

挂载点：``/api/approval/*``。

为前端 ``frontend/src/api/approval.ts`` 提供数据源；底层使用
``app/db/models/approval.py`` 中的 ORM 模型，每个状态变更同时写入
``approval_records`` 与 ``ai_action_audit``，构建完整审计轨迹。
"""

from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.application.mobile_push_app_service import notify_mobile_user
from app.db.models.approval import (
    ApprovalAction,
    ApprovalFlow,
    ApprovalFlowNode,
    ApprovalRecord,
    ApprovalRequest,
    ApprovalStatus,
)
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/approval", tags=["approval"])


# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #


def _resolve_actor(x_user_id: str | None, fallback: int | None = None) -> int | None:
    """从 ``X-User-ID`` 请求头解析当前用户 ID。"""
    if x_user_id and str(x_user_id).strip().isdigit():
        return int(str(x_user_id).strip())
    if fallback is not None:
        try:
            return int(fallback)
        except (TypeError, ValueError):
            return None
    return None


def _audit(db, *, actor: int | None, action: str, payload: dict) -> None:
    """写入 ``ai_action_audit``：跨业务的 DB 操作轨迹。"""
    try:
        db.execute(
            text(
                "INSERT INTO ai_action_audit (actor, action, payload) VALUES (:actor, :action, :payload)"
            ),
            {
                "actor": str(actor) if actor is not None else None,
                "action": action,
                "payload": json.dumps(payload, ensure_ascii=False, default=str),
            },
        )
    except Exception as exc:  # pragma: no cover - 审计失败不应阻塞主流程
        logger.warning("ai_action_audit 写入失败 action=%s: %s", action, exc)


def _generate_request_no() -> str:
    """生成审批单号，例如 ``APR20260419-AB12CD``。"""
    return f"APR{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"


def _node_query_for_user(node: ApprovalFlowNode, user_id: int) -> bool:
    """判断 ``user_id`` 是否在节点的审批人列表中。"""
    if not node or not node.approver_ids:
        return False
    try:
        ids = (
            json.loads(node.approver_ids)
            if isinstance(node.approver_ids, str)
            else node.approver_ids
        )
    except (ValueError, TypeError):
        return False
    if not isinstance(ids, list):
        return False
    try:
        return int(user_id) in [int(x) for x in ids if x is not None]
    except (TypeError, ValueError):
        return False


def _ordered_nodes(db, flow_id: int) -> list[ApprovalFlowNode]:
    return (
        db.query(ApprovalFlowNode)
        .filter(
            ApprovalFlowNode.flow_id == flow_id, ApprovalFlowNode.is_active == True
        )  # noqa: E712
        .order_by(ApprovalFlowNode.node_order.asc())
        .all()
    )


def _next_node(nodes: list[ApprovalFlowNode], current_order: int) -> ApprovalFlowNode | None:
    for n in nodes:
        if n.node_order > current_order:
            return n
    return None


def _request_to_dict(req: ApprovalRequest, *, include_records: bool = False) -> dict[str, Any]:
    """统一序列化（含 ``records`` 时间线，便于详情视图渲染）。"""
    base = req.to_dict()
    if include_records:
        records = (
            sorted(req.records or [], key=lambda r: r.action_time or datetime.min)
            if req.records
            else []
        )
        base["records"] = [r.to_dict() for r in records]
    return base


# --------------------------------------------------------------------------- #
# 审批请求
# --------------------------------------------------------------------------- #


@router.get("/requests")
def list_requests(
    approver_id: int | None = Query(default=None),
    applicant_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    business_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
):
    """列表接口：支持按申请人 / 当前审批人 / 状态过滤。"""
    with get_db() as db:
        query = db.query(ApprovalRequest)

        if applicant_id is not None:
            query = query.filter(ApprovalRequest.applicant_id == applicant_id)

        if status:
            query = query.filter(ApprovalRequest.status == status)
        else:
            query = query.filter(
                ApprovalRequest.status.in_(
                    [
                        ApprovalStatus.PENDING.value,
                        ApprovalStatus.IN_PROGRESS.value,
                        ApprovalStatus.APPROVED.value,
                        ApprovalStatus.REJECTED.value,
                        ApprovalStatus.WITHDRAWN.value,
                        ApprovalStatus.CANCELLED.value,
                    ]
                )
            )

        if business_type:
            query = query.filter(ApprovalRequest.business_type == business_type)

        query = query.order_by(ApprovalRequest.created_at.desc())
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        # 当前审批人过滤需要解析节点的 approver_ids JSON，无法在 SQL 端表达，故在 Python 中筛选。
        result: list[dict[str, Any]] = []
        for req in items:
            data = _request_to_dict(req, include_records=False)
            if approver_id is not None:
                node = req.current_node
                if not node or not _node_query_for_user(node, approver_id):
                    continue
                if req.status not in (
                    ApprovalStatus.PENDING.value,
                    ApprovalStatus.IN_PROGRESS.value,
                ):
                    continue
            result.append(data)

        return {
            "success": True,
            "data": result,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "returned": len(result),
            },
        }


@router.post("/requests/cleanup")
def cleanup_requests(
    body: dict = Body(default_factory=dict),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    """批量清理已完成的审批记录。

    Body 参数::

        {
          "statuses": ["approved", "rejected", "withdrawn", "cancelled"],
                              # 或 "all" / "completed"；默认全部终态
          "before_days": 0,    # 仅清理 N 天之前的记录；0/不传表示不限
          "scope": "self",    # "self" 仅清理本人（默认）；其他值暂不支持
          "dry_run": false    # true 时只返回待清理数量，不真正删除
        }
    """
    actor = _resolve_actor(x_user_id, fallback=body.get("user_id"))
    if actor is None:
        raise HTTPException(status_code=401, detail="缺少 X-User-ID")

    statuses = _normalize_statuses(body.get("statuses") or body.get("status"))
    dry_run = bool(body.get("dry_run", False))

    before_days_raw = body.get("before_days")
    before_days: int | None
    try:
        before_days = int(before_days_raw) if before_days_raw not in (None, "", 0) else None
    except (TypeError, ValueError):
        before_days = None
    if before_days is not None and before_days < 0:
        before_days = None

    scope = str(body.get("scope") or "self").strip() or "self"
    if scope != "self":
        return JSONResponse(
            {"success": False, "message": f"暂不支持的清理范围：{scope}"},
            status_code=400,
        )

    with get_db() as db:
        query = db.query(ApprovalRequest).filter(
            ApprovalRequest.applicant_id == actor,
            ApprovalRequest.status.in_(statuses),
        )
        if before_days is not None:
            from datetime import timedelta

            cutoff = datetime.now() - timedelta(days=before_days)
            query = query.filter(ApprovalRequest.created_at < cutoff)

        items = query.all()
        matched = len(items)

        if dry_run or matched == 0:
            return {
                "success": True,
                "data": {
                    "matched": matched,
                    "deleted": 0,
                    "dry_run": dry_run,
                    "statuses": statuses,
                    "before_days": before_days,
                },
            }

        ids = [req.id for req in items]
        nos = [req.request_no for req in items]

        _audit(
            db,
            actor=actor,
            action="approval.cleanup",
            payload={
                "count": matched,
                "statuses": statuses,
                "before_days": before_days,
                "request_ids": ids[:500],
                "request_nos": nos[:500],
            },
        )

        for req in items:
            db.delete(req)
        db.commit()

        return {
            "success": True,
            "data": {
                "matched": matched,
                "deleted": matched,
                "dry_run": False,
                "statuses": statuses,
                "before_days": before_days,
            },
        }


@router.get("/requests/{request_id}")
def get_request_detail(request_id: int):
    with get_db() as db:
        req = db.query(ApprovalRequest).filter(ApprovalRequest.id == request_id).first()
        if not req:
            return JSONResponse(
                {"success": False, "message": "审批请求不存在", "data": None},
                status_code=404,
            )
        return {"success": True, "data": _request_to_dict(req, include_records=True)}


@router.post("/requests")
def submit_request(
    body: dict = Body(default_factory=dict),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    """提交一个新的审批请求；按 ``flow_key`` 找到流程并定位首个有效节点。"""
    flow_key = str(body.get("flow_key") or "").strip()
    business_type = str(body.get("business_type") or "general").strip()
    title = str(body.get("title") or "").strip()
    if not flow_key or not title:
        raise HTTPException(status_code=400, detail="flow_key 与 title 为必填项")

    actor = _resolve_actor(x_user_id, fallback=body.get("applicant_id"))
    if actor is None:
        raise HTTPException(status_code=401, detail="缺少 X-User-ID 或 applicant_id")

    business_id = body.get("business_id")
    business_data = body.get("business_data")
    description = str(body.get("description") or "").strip() or None
    applicant_name = str(body.get("applicant_name") or "").strip() or None
    applicant_department = str(body.get("applicant_department") or "").strip() or None
    priority = str(body.get("priority") or "normal").strip() or "normal"

    with get_db() as db:
        flow = (
            db.query(ApprovalFlow)
            .filter(ApprovalFlow.flow_key == flow_key, ApprovalFlow.is_active == True)  # noqa: E712
            .first()
        )
        if not flow:
            return JSONResponse(
                {"success": False, "message": f"未找到启用的审批流程：{flow_key}", "data": None},
                status_code=404,
            )

        nodes = _ordered_nodes(db, flow.id)
        if not nodes:
            return JSONResponse(
                {"success": False, "message": "审批流程未配置任何启用节点", "data": None},
                status_code=400,
            )
        first_node = nodes[0]

        req = ApprovalRequest(
            request_no=_generate_request_no(),
            flow_id=flow.id,
            business_type=business_type,
            business_id=(
                int(business_id)
                if isinstance(business_id, (int, str)) and str(business_id).isdigit()
                else None
            ),
            business_data=json.dumps(business_data, ensure_ascii=False) if business_data else None,
            applicant_id=actor,
            applicant_name=applicant_name,
            applicant_department=applicant_department,
            title=title,
            description=description,
            current_node_id=first_node.id,
            current_node_order=first_node.node_order,
            status=ApprovalStatus.PENDING.value,
            priority=priority,
        )
        db.add(req)
        db.flush()

        _audit(
            db,
            actor=actor,
            action="approval.submit",
            payload={
                "request_id": req.id,
                "request_no": req.request_no,
                "flow_id": flow.id,
                "flow_key": flow.flow_key,
                "business_type": business_type,
                "business_id": req.business_id,
                "first_node_id": first_node.id,
            },
        )
        db.commit()
        db.refresh(req)

        return {"success": True, "data": _request_to_dict(req, include_records=True)}


def _close_request_if_needed(
    db,
    *,
    req: ApprovalRequest,
    nodes: list[ApprovalFlowNode],
    approver_id: int,
    approver_name: str | None,
) -> tuple[str, int | None]:
    """串行流程：推进到下一节点；若已到末节点则置为 ``approved``。"""
    next_node = _next_node(nodes, req.current_node_order or 0)
    if next_node is None:
        req.status = ApprovalStatus.APPROVED.value
        req.approved_at = datetime.now()
        req.approved_by = approver_id
        req.approved_by_name = approver_name
        req.current_node_id = None
        req.current_node_order = (req.current_node_order or 0) + 1
        return ApprovalStatus.APPROVED.value, None
    req.status = ApprovalStatus.IN_PROGRESS.value
    req.current_node_id = next_node.id
    req.current_node_order = next_node.node_order
    return ApprovalStatus.IN_PROGRESS.value, next_node.id


@router.post("/requests/{request_id}/approve")
def approve_request(
    request_id: int,
    body: dict = Body(default_factory=dict),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    actor = _resolve_actor(x_user_id, fallback=body.get("approver_id"))
    if actor is None:
        raise HTTPException(status_code=401, detail="缺少 X-User-ID 或 approver_id")

    opinion = str(body.get("opinion") or "").strip() or "同意"
    approver_name = str(body.get("approver_name") or "").strip() or None

    with get_db() as db:
        req = db.query(ApprovalRequest).filter(ApprovalRequest.id == request_id).first()
        if not req:
            return JSONResponse(
                {"success": False, "message": "审批请求不存在"},
                status_code=404,
            )
        if req.status not in (ApprovalStatus.PENDING.value, ApprovalStatus.IN_PROGRESS.value):
            return JSONResponse(
                {"success": False, "message": f"当前状态不可审批：{req.status}"},
                status_code=400,
            )

        current_node = req.current_node
        if current_node is None:
            return JSONResponse(
                {"success": False, "message": "审批请求缺少当前节点"},
                status_code=400,
            )
        if not _node_query_for_user(current_node, actor):
            return JSONResponse(
                {"success": False, "message": "当前用户不在审批人列表中"},
                status_code=403,
            )

        status_before = req.status
        node_id_before = current_node.id

        record = ApprovalRecord(
            request_id=req.id,
            node_id=current_node.id,
            node_name=current_node.node_name,
            node_order=current_node.node_order,
            approver_id=actor,
            approver_name=approver_name,
            action=ApprovalAction.APPROVE.value,
            opinion=opinion,
            is_passed=True,
        )
        db.add(record)

        nodes = _ordered_nodes(db, req.flow_id)
        new_status, next_node_id = _close_request_if_needed(
            db,
            req=req,
            nodes=nodes,
            approver_id=actor,
            approver_name=approver_name,
        )

        _audit(
            db,
            actor=actor,
            action="approval.approve",
            payload={
                "request_id": req.id,
                "request_no": req.request_no,
                "flow_id": req.flow_id,
                "node_id": node_id_before,
                "next_node_id": next_node_id,
                "status_before": status_before,
                "status_after": new_status,
                "opinion": opinion,
            },
        )

        db.commit()
        db.refresh(req)
        if req.applicant_id:
            notify_mobile_user(
                int(req.applicant_id),
                "审批进度更新",
                f"《{req.title or req.request_no}》已处理",
                {"route": f"/app/approval/{req.id}", "request_id": str(req.id)},
            )
        return {"success": True, "data": _request_to_dict(req, include_records=True)}


@router.post("/requests/{request_id}/reject")
def reject_request(
    request_id: int,
    body: dict = Body(default_factory=dict),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    actor = _resolve_actor(x_user_id, fallback=body.get("approver_id"))
    if actor is None:
        raise HTTPException(status_code=401, detail="缺少 X-User-ID 或 approver_id")

    reason = str(body.get("reason") or body.get("opinion") or "").strip()
    if not reason:
        raise HTTPException(status_code=400, detail="拒绝原因不能为空")

    approver_name = str(body.get("approver_name") or "").strip() or None

    with get_db() as db:
        req = db.query(ApprovalRequest).filter(ApprovalRequest.id == request_id).first()
        if not req:
            return JSONResponse(
                {"success": False, "message": "审批请求不存在"},
                status_code=404,
            )
        if req.status not in (ApprovalStatus.PENDING.value, ApprovalStatus.IN_PROGRESS.value):
            return JSONResponse(
                {"success": False, "message": f"当前状态不可拒绝：{req.status}"},
                status_code=400,
            )

        current_node = req.current_node
        if current_node is None:
            return JSONResponse(
                {"success": False, "message": "审批请求缺少当前节点"},
                status_code=400,
            )
        if not _node_query_for_user(current_node, actor):
            return JSONResponse(
                {"success": False, "message": "当前用户不在审批人列表中"},
                status_code=403,
            )

        status_before = req.status
        node_id_before = current_node.id

        record = ApprovalRecord(
            request_id=req.id,
            node_id=current_node.id,
            node_name=current_node.node_name,
            node_order=current_node.node_order,
            approver_id=actor,
            approver_name=approver_name,
            action=ApprovalAction.REJECT.value,
            opinion=reason,
            reject_reason=reason,
            is_passed=False,
        )
        db.add(record)

        req.status = ApprovalStatus.REJECTED.value
        req.rejected_at = datetime.now()
        req.rejection_reason = reason

        _audit(
            db,
            actor=actor,
            action="approval.reject",
            payload={
                "request_id": req.id,
                "request_no": req.request_no,
                "flow_id": req.flow_id,
                "node_id": node_id_before,
                "status_before": status_before,
                "status_after": req.status,
                "reason": reason,
            },
        )

        db.commit()
        db.refresh(req)
        return {"success": True, "data": _request_to_dict(req, include_records=True)}


@router.post("/requests/{request_id}/withdraw")
def withdraw_request(
    request_id: int,
    body: dict = Body(default_factory=dict),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    actor = _resolve_actor(x_user_id, fallback=body.get("user_id"))
    if actor is None:
        raise HTTPException(status_code=401, detail="缺少 X-User-ID")

    with get_db() as db:
        req = db.query(ApprovalRequest).filter(ApprovalRequest.id == request_id).first()
        if not req:
            return JSONResponse(
                {"success": False, "message": "审批请求不存在"},
                status_code=404,
            )
        if req.applicant_id != actor:
            return JSONResponse(
                {"success": False, "message": "只有申请人可以撤回"},
                status_code=403,
            )
        if req.status not in (ApprovalStatus.PENDING.value, ApprovalStatus.IN_PROGRESS.value):
            return JSONResponse(
                {"success": False, "message": f"当前状态不可撤回：{req.status}"},
                status_code=400,
            )

        flow = req.flow
        if flow is not None and flow.allow_withdraw is False:
            return JSONResponse(
                {"success": False, "message": "该流程不允许撤回"},
                status_code=400,
            )

        status_before = req.status
        current_node = req.current_node

        record = ApprovalRecord(
            request_id=req.id,
            node_id=current_node.id if current_node else 0,
            node_name=current_node.node_name if current_node else "",
            node_order=current_node.node_order if current_node else 0,
            approver_id=actor,
            action=ApprovalAction.WITHDRAW.value,
            opinion="申请人撤回",
            is_passed=False,
        )
        db.add(record)

        req.status = ApprovalStatus.WITHDRAWN.value

        _audit(
            db,
            actor=actor,
            action="approval.withdraw",
            payload={
                "request_id": req.id,
                "request_no": req.request_no,
                "flow_id": req.flow_id,
                "status_before": status_before,
                "status_after": req.status,
            },
        )

        db.commit()
        db.refresh(req)
        return {"success": True, "data": _request_to_dict(req, include_records=True)}


# --------------------------------------------------------------------------- #
# 清理 / 删除
# --------------------------------------------------------------------------- #

# 允许删除的"终态"状态（进行中的申请必须先撤回才能删除）
_FINAL_STATUSES: tuple[str, ...] = (
    ApprovalStatus.APPROVED.value,
    ApprovalStatus.REJECTED.value,
    ApprovalStatus.WITHDRAWN.value,
    ApprovalStatus.CANCELLED.value,
)


def _normalize_statuses(raw: Any) -> list[str]:
    """标准化前端传入的状态过滤参数。"""
    if raw is None:
        return list(_FINAL_STATUSES)
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw or raw in ("all", "completed", "final"):
            return list(_FINAL_STATUSES)
        raw = [s.strip() for s in raw.split(",") if s.strip()]
    if not isinstance(raw, list):
        return list(_FINAL_STATUSES)
    allowed = set(_FINAL_STATUSES)
    result = [s for s in (str(x).strip() for x in raw) if s in allowed]
    return result or list(_FINAL_STATUSES)


@router.delete("/requests/{request_id}")
def delete_request(
    request_id: int,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    """物理删除单个审批申请（仅申请人本人，且必须处于终态）。

    级联删除 ``approval_records``；会写入一条 ``approval.delete`` 审计。
    """
    actor = _resolve_actor(x_user_id)
    if actor is None:
        raise HTTPException(status_code=401, detail="缺少 X-User-ID")

    with get_db() as db:
        req = db.query(ApprovalRequest).filter(ApprovalRequest.id == request_id).first()
        if not req:
            return JSONResponse(
                {"success": False, "message": "审批请求不存在"},
                status_code=404,
            )
        if req.applicant_id != actor:
            return JSONResponse(
                {"success": False, "message": "只有申请人可以删除自己的审批记录"},
                status_code=403,
            )
        if req.status not in _FINAL_STATUSES:
            return JSONResponse(
                {
                    "success": False,
                    "message": f"进行中的审批不能删除，请先撤回（当前状态：{req.status}）",
                },
                status_code=400,
            )

        snapshot = {
            "request_id": req.id,
            "request_no": req.request_no,
            "flow_id": req.flow_id,
            "business_type": req.business_type,
            "business_id": req.business_id,
            "title": req.title,
            "status": req.status,
        }

        _audit(db, actor=actor, action="approval.delete", payload=snapshot)
        db.delete(req)
        db.commit()
        return {"success": True, "data": {"deleted": 1, "request_id": request_id}}


# --------------------------------------------------------------------------- #
# 审批流程
# --------------------------------------------------------------------------- #


@router.get("/users")
def get_approval_users():
    """返回可选审批人列表（从用户/人员表拉取）。

    供前端审批流程配置页的「审批人选择」下拉使用。
    若无独立 User 表，则 fallback 到产品/人员 roster（考勤行业）。
    """
    users: list[dict] = []
    try:
        from app.db.models import User  # type: ignore

        with get_db() as db:
            rows = db.query(User).filter(User.is_active == True).all()  # noqa: E712
            users = [
                {
                    "id": u.id,
                    "name": getattr(u, "name", None) or getattr(u, "username", "") or f"用户{u.id}",
                    "email": getattr(u, "email", None),
                    "department": getattr(u, "department", None),
                }
                for u in rows
            ]
    except Exception:
        pass

    if not users:
        try:
            from app.application import get_product_app_service

            products = get_product_app_service().get_all_products()
            if isinstance(products, list):
                for p in products[:50]:
                    name = str(p.get("name") or p.get("product_name") or "").strip()
                    if name:
                        users.append({"id": p.get("id"), "name": name, "source": "roster"})
        except Exception:
            pass

    return {"success": True, "data": users, "count": len(users)}


@router.get("/users/{user_id}/orphan-check")
def check_approver_orphan(user_id: int):
    """检查某用户 ID 是否出现在激活流程的审批节点但在用户表中已不存在（孤儿检测）。"""
    with get_db() as db:
        active_flows = (
            db.query(ApprovalFlow)
            .filter(
                ApprovalFlow.is_active == True,
                ApprovalFlow.is_deleted == False,  # noqa: E712
            )
            .all()
        )
        orphan_flows: list[dict] = []
        for flow in active_flows:
            for node in flow.nodes or []:
                ids = []
                try:
                    ids = json.loads(node.approver_ids or "[]")
                except Exception:
                    pass
                if user_id in ids:
                    orphan_flows.append(
                        {"flow_id": flow.id, "flow_name": flow.flow_name, "node_id": node.id}
                    )
        is_orphan = len(orphan_flows) > 0
        return {
            "success": True,
            "user_id": user_id,
            "is_orphan_in_active_flows": is_orphan,
            "orphan_flows": orphan_flows,
            "message": f"用户 {user_id} {'出现在以下激活流程节点中但可能已不存在' if is_orphan else '未在任何激活流程节点中'}",
        }


@router.post("/process-timeouts")
def process_approval_timeouts_endpoint():
    """手动触发（或由定时任务调用）审批超时处理——扫描 expired_at < now 的待审批记录。"""
    from app.application.workflow.approval_service import process_approval_timeouts

    result = process_approval_timeouts()
    return JSONResponse(result, status_code=200 if result.get("success") else 500)


@router.get("/flows")
def list_flows(
    is_active: bool | None = Query(default=None),
    business_type: str | None = Query(default=None),
):
    with get_db() as db:
        query = db.query(ApprovalFlow).filter(ApprovalFlow.is_deleted == False)  # noqa: E712
        if is_active is not None:
            query = query.filter(ApprovalFlow.is_active == bool(is_active))
        if business_type:
            query = query.filter(ApprovalFlow.business_type == business_type)
        query = query.order_by(ApprovalFlow.created_at.desc())
        flows = query.all()
        return {
            "success": True,
            "data": [flow.to_dict() for flow in flows],
        }


@router.get("/flows/{flow_id}")
def get_flow_detail(flow_id: int):
    with get_db() as db:
        flow = db.query(ApprovalFlow).filter(ApprovalFlow.id == flow_id).first()
        if not flow:
            return JSONResponse(
                {"success": False, "message": "审批流程不存在", "data": None},
                status_code=404,
            )
        return {"success": True, "data": flow.to_dict()}


@router.post("/flows")
def create_flow(
    body: dict = Body(default_factory=dict),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    """创建审批流程；body 形如 ``{flow: {...}, nodes: [...]}``。"""
    flow_payload = body.get("flow") or {}
    nodes_payload = body.get("nodes") or []
    if not isinstance(flow_payload, dict) or not isinstance(nodes_payload, list):
        raise HTTPException(status_code=400, detail="flow / nodes 字段格式错误")

    flow_name = str(flow_payload.get("flow_name") or "").strip()
    flow_key = str(flow_payload.get("flow_key") or "").strip()
    business_type = str(flow_payload.get("business_type") or "general").strip() or "general"
    if not flow_name or not flow_key:
        raise HTTPException(status_code=400, detail="flow_name / flow_key 为必填项")
    if not nodes_payload:
        raise HTTPException(status_code=400, detail="至少需要一个审批节点")

    actor = _resolve_actor(x_user_id, fallback=flow_payload.get("created_by"))

    with get_db() as db:
        existed = (
            db.query(ApprovalFlow)
            .filter(
                ApprovalFlow.flow_key == flow_key, ApprovalFlow.is_deleted == False
            )  # noqa: E712
            .first()
        )
        if existed:
            return JSONResponse(
                {"success": False, "message": f"flow_key 已存在：{flow_key}"},
                status_code=409,
            )

        flow = ApprovalFlow(
            flow_key=flow_key,
            flow_name=flow_name,
            description=str(flow_payload.get("description") or "").strip() or None,
            industry=str(flow_payload.get("industry") or "通用").strip() or "通用",
            business_type=business_type,
            node_type=str(flow_payload.get("node_type") or "serial"),
            allow_transfer=bool(flow_payload.get("allow_transfer", True)),
            allow_delegate=bool(flow_payload.get("allow_delegate", False)),
            allow_withdraw=bool(flow_payload.get("allow_withdraw", True)),
            timeout_hours=int(flow_payload.get("timeout_hours") or 48),
            is_active=bool(flow_payload.get("is_active", True)),
            is_deleted=False,
            created_by=actor,
        )
        db.add(flow)
        db.flush()

        for idx, node_data in enumerate(nodes_payload, start=1):
            if not isinstance(node_data, dict):
                continue
            approver_ids = node_data.get("approver_ids") or []
            if not isinstance(approver_ids, list):
                approver_ids = []
            node = ApprovalFlowNode(
                flow_id=flow.id,
                node_name=str(node_data.get("node_name") or f"节点{idx}").strip(),
                node_order=int(node_data.get("node_order") or idx),
                node_type=str(node_data.get("node_type") or "serial"),
                approver_type=str(node_data.get("approver_type") or "user"),
                approver_ids=json.dumps(
                    [int(x) for x in approver_ids if str(x).strip().lstrip("-").isdigit()],
                    ensure_ascii=False,
                ),
                min_approvals=int(node_data.get("min_approvals") or 1),
                condition_expression=node_data.get("condition_expression") or None,
                condition_description=node_data.get("condition_description") or None,
                timeout_hours=node_data.get("timeout_hours"),
                timeout_action=str(node_data.get("timeout_action") or "notify"),
                is_active=bool(node_data.get("is_active", True)),
            )
            db.add(node)

        _audit(
            db,
            actor=actor,
            action="approval.flow.create",
            payload={
                "flow_id": flow.id,
                "flow_key": flow_key,
                "flow_name": flow_name,
                "business_type": business_type,
                "node_count": len(nodes_payload),
            },
        )

        db.commit()
        db.refresh(flow)
        return {"success": True, "data": flow.to_dict()}


@router.put("/flows/{flow_id}")
def update_flow(
    flow_id: int,
    body: dict = Body(default_factory=dict),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    """更新审批流程基础信息（不含节点，节点暂由 POST /flows 重建）。"""
    actor = _resolve_actor(x_user_id)
    with get_db() as db:
        flow = (
            db.query(ApprovalFlow)
            .filter(ApprovalFlow.id == flow_id, ApprovalFlow.is_deleted == False)  # noqa: E712
            .first()
        )
        if not flow:
            return JSONResponse({"success": False, "message": "审批流程不存在"}, status_code=404)

        updatable = [
            "flow_name",
            "description",
            "industry",
            "business_type",
            "node_type",
            "allow_transfer",
            "allow_delegate",
            "allow_withdraw",
            "timeout_hours",
        ]
        for field in updatable:
            if field in body:
                setattr(flow, field, body[field])

        flow.updated_at = datetime.utcnow()
        _audit(db, actor=actor, action="approval_flow_update", payload={"flow_id": flow_id, **body})
        db.commit()
        db.refresh(flow)
        return {"success": True, "data": flow.to_dict()}


@router.patch("/flows/{flow_id}/active")
def toggle_flow_active(
    flow_id: int,
    body: dict = Body(default_factory=dict),
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    """启用 / 停用审批流程。body: {is_active: bool}"""
    actor = _resolve_actor(x_user_id)
    is_active = bool(body.get("is_active", True))
    with get_db() as db:
        flow = (
            db.query(ApprovalFlow)
            .filter(ApprovalFlow.id == flow_id, ApprovalFlow.is_deleted == False)  # noqa: E712
            .first()
        )
        if not flow:
            return JSONResponse({"success": False, "message": "审批流程不存在"}, status_code=404)
        flow.is_active = is_active
        flow.updated_at = datetime.utcnow()
        _audit(
            db,
            actor=actor,
            action="approval_flow_toggle_active",
            payload={"flow_id": flow_id, "is_active": is_active},
        )
        db.commit()
        return {
            "success": True,
            "message": f"流程已{'启用' if is_active else '停用'}",
            "is_active": is_active,
        }


@router.delete("/flows/{flow_id}")
def delete_flow(
    flow_id: int,
    x_user_id: str | None = Header(default=None, alias="X-User-ID"),
):
    """软删除审批流程（is_deleted = True）。"""
    actor = _resolve_actor(x_user_id)
    with get_db() as db:
        flow = (
            db.query(ApprovalFlow)
            .filter(ApprovalFlow.id == flow_id, ApprovalFlow.is_deleted == False)  # noqa: E712
            .first()
        )
        if not flow:
            return JSONResponse(
                {"success": False, "message": "审批流程不存在或已删除"}, status_code=404
            )
        # 检查是否有进行中的审批请求
        pending_count = (
            db.query(ApprovalRequest)
            .filter(
                ApprovalRequest.flow_id == flow_id,
                ApprovalRequest.status == ApprovalStatus.PENDING,
            )
            .count()
        )
        if pending_count > 0:
            return JSONResponse(
                {"success": False, "message": f"流程下有 {pending_count} 条待审批请求，无法删除"},
                status_code=409,
            )
        flow.is_deleted = True
        flow.is_active = False
        flow.updated_at = datetime.utcnow()
        _audit(db, actor=actor, action="approval_flow_delete", payload={"flow_id": flow_id})
        db.commit()
        return {"success": True, "message": "审批流程已删除"}
