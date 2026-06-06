from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/service-bridge", tags=["service-bridge"])

_INSTANCE_ID_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", ".service_bridge_instance_id"
)


def _get_or_create_instance_id() -> str:
    try:
        os.makedirs(os.path.dirname(_INSTANCE_ID_FILE), exist_ok=True)
        if os.path.exists(_INSTANCE_ID_FILE):
            with open(_INSTANCE_ID_FILE, "r", encoding="utf-8") as f:
                cached = f.read().strip()
                if cached:
                    return cached
        instance_id = f"xcagi-host-{uuid.uuid4().hex[:8]}"
        with open(_INSTANCE_ID_FILE, "w", encoding="utf-8") as f:
            f.write(instance_id)
        return instance_id
    except Exception:
        return f"xcagi-host-{uuid.uuid4().hex[:8]}"


def _get_instance_name() -> str:
    return os.environ.get("SERVICE_BRIDGE_INSTANCE_NAME", "XCAGI 宿主")


def _get_config_value(key: str, default: str = "") -> str:
    with get_db() as db:
        from app.db.models.service_request import ServiceBridgeConfig

        cfg = db.query(ServiceBridgeConfig).filter(ServiceBridgeConfig.config_key == key).first()
        if cfg:
            return cfg.config_value
    env_key = f"SERVICE_BRIDGE_{key.upper()}"
    return os.environ.get(env_key, default)


def _set_config_value(key: str, value: str, description: str = "") -> None:
    with get_db() as db:
        from app.db.models.service_request import ServiceBridgeConfig

        cfg = db.query(ServiceBridgeConfig).filter(ServiceBridgeConfig.config_key == key).first()
        if cfg:
            cfg.config_value = value
            if description:
                cfg.description = description
        else:
            cfg = ServiceBridgeConfig(config_key=key, config_value=value, description=description)
            db.add(cfg)


class ServiceRequestCreate(BaseModel):
    source_instance_id: str = Field(..., max_length=128)
    source_instance_name: str = Field(..., max_length=128)
    request_type: str = Field(default="general", max_length=64)
    title: str = Field(..., max_length=256)
    description: Optional[str] = None
    priority: str = Field(default="normal", max_length=16)
    extra_data: Optional[str] = None


class ServiceRequestRespond(BaseModel):
    response: str
    responded_by: Optional[str] = None
    status: str = Field(default="resolved", max_length=32)


class InstanceRegister(BaseModel):
    instance_id: str = Field(..., max_length=128)
    instance_name: str = Field(..., max_length=128)
    instance_url: Optional[str] = None
    description: Optional[str] = None


class OutboxCreate(BaseModel):
    request_type: str = Field(default="general", max_length=64)
    title: str = Field(..., max_length=256)
    description: Optional[str] = None
    priority: str = Field(default="normal", max_length=16)
    extra_data: Optional[str] = None


class BridgeConfigUpdate(BaseModel):
    main_server_url: Optional[str] = None
    instance_name: Optional[str] = None


@router.get("/config")
async def get_config():
    instance_id = _get_or_create_instance_id()
    instance_name = _get_instance_name()
    main_server_url = _get_config_value("main_server_url", "")
    return {
        "ok": True,
        "data": {
            "instance_id": instance_id,
            "instance_name": instance_name,
            "main_server_url": main_server_url,
        },
    }


@router.put("/config")
async def update_config(body: BridgeConfigUpdate):
    if body.main_server_url is not None:
        _set_config_value("main_server_url", body.main_server_url, "主软件服务器地址")
    if body.instance_name is not None:
        _set_config_value("instance_name", body.instance_name, "本实例名称")
    return {"ok": True, "message": "配置已更新"}


@router.post("/requests")
async def receive_request(body: ServiceRequestCreate):
    with get_db() as db:
        from app.db.models.service_request import (
            ServiceRequest,
            ServiceRequestPriority,
            ServiceRequestStatus,
        )

        valid_priorities = [p.value for p in ServiceRequestPriority]
        if body.priority not in valid_priorities:
            raise HTTPException(
                status_code=400, detail=f"Invalid priority. Must be one of: {valid_priorities}"
            )

        req = ServiceRequest(
            source_instance_id=body.source_instance_id,
            source_instance_name=body.source_instance_name,
            request_type=body.request_type,
            title=body.title,
            description=body.description,
            priority=body.priority,
            status=ServiceRequestStatus.PENDING.value,
            extra_data=body.extra_data,
        )
        db.add(req)
        db.flush()
        result = req.to_dict()
    logger.info("Received service request from %s: %s", body.source_instance_name, body.title)
    return {"ok": True, "data": result}


@router.get("/requests")
async def list_requests(
    status: Optional[str] = None,
    source_instance_id: Optional[str] = None,
    request_type: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
):
    with get_db() as db:
        from app.db.models.service_request import ServiceRequest

        q = db.query(ServiceRequest)
        if status:
            q = q.filter(ServiceRequest.status == status)
        if source_instance_id:
            q = q.filter(ServiceRequest.source_instance_id == source_instance_id)
        if request_type:
            q = q.filter(ServiceRequest.request_type == request_type)
        total = q.count()
        items = (
            q.order_by(ServiceRequest.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
            .all()
        )
        return {
            "ok": True,
            "data": [item.to_dict() for item in items],
            "total": total,
            "page": page,
            "per_page": per_page,
        }


@router.get("/requests/{request_id}")
async def get_request(request_id: int):
    with get_db() as db:
        from app.db.models.service_request import ServiceRequest

        req = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")
        return {"ok": True, "data": req.to_dict()}


@router.put("/requests/{request_id}/respond")
async def respond_request(request_id: int, body: ServiceRequestRespond):
    from app.db.models.service_request import ServiceRequestStatus

    valid_statuses = [
        ServiceRequestStatus.PROCESSING.value,
        ServiceRequestStatus.RESOLVED.value,
        ServiceRequestStatus.CLOSED.value,
    ]
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}"
        )

    with get_db() as db:
        from app.db.models.service_request import ServiceRequest

        req = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
        if not req:
            raise HTTPException(status_code=404, detail="Request not found")
        req.response = body.response
        req.responded_by = body.responded_by
        req.responded_at = datetime.now(timezone.utc)
        req.status = body.status
        db.flush()
        result = req.to_dict()
    logger.info("Responded to service request %d from %s", request_id, req.source_instance_name)
    return {"ok": True, "data": result}


@router.get("/instances")
async def list_instances():
    with get_db() as db:
        from sqlalchemy import func

        from app.db.models.service_request import ServiceRequest, ServiceRequestStatus

        rows = (
            db.query(
                ServiceRequest.source_instance_id,
                ServiceRequest.source_instance_name,
                func.count(ServiceRequest.id).label("total_requests"),
                func.count()
                .filter(ServiceRequest.status == ServiceRequestStatus.PENDING.value)
                .label("pending_count"),
            )
            .group_by(ServiceRequest.source_instance_id, ServiceRequest.source_instance_name)
            .all()
        )
        return {
            "ok": True,
            "data": [
                {
                    "instance_id": r.source_instance_id,
                    "instance_name": r.source_instance_name,
                    "total_requests": r.total_requests,
                    "pending_count": int(r.pending_count or 0),
                }
                for r in rows
            ],
        }


@router.get("/stats")
async def get_stats():
    with get_db() as db:
        from sqlalchemy import func

        from app.db.models.service_request import ServiceRequest

        total = db.query(func.count(ServiceRequest.id)).scalar() or 0
        pending = (
            db.query(func.count(ServiceRequest.id))
            .filter(ServiceRequest.status == "pending")
            .scalar()
            or 0
        )
        processing = (
            db.query(func.count(ServiceRequest.id))
            .filter(ServiceRequest.status == "processing")
            .scalar()
            or 0
        )
        resolved = (
            db.query(func.count(ServiceRequest.id))
            .filter(ServiceRequest.status == "resolved")
            .scalar()
            or 0
        )
        return {
            "ok": True,
            "data": {
                "total": total,
                "pending": pending,
                "processing": processing,
                "resolved": resolved,
            },
        }


@router.post("/outbox")
async def send_outbox(body: OutboxCreate):
    """子实例/离线端：本地落库并转发到 main_server_url（默认同机则直写当前库）。"""
    instance_id = _get_or_create_instance_id()
    instance_name = _get_config_value("instance_name", _get_instance_name())
    main_server_url = (_get_config_value("main_server_url", "") or "").strip().rstrip("/")

    from app.db.models.service_request import ServiceRequest, ServiceRequestPriority

    valid_priorities = [p.value for p in ServiceRequestPriority]
    if body.priority not in valid_priorities:
        raise HTTPException(
            status_code=400, detail=f"Invalid priority. Must be one of: {valid_priorities}"
        )

    payload = {
        "source_instance_id": instance_id,
        "source_instance_name": instance_name,
        "request_type": body.request_type,
        "title": body.title,
        "description": body.description,
        "priority": body.priority,
        "extra_data": body.extra_data,
    }

    if not main_server_url:
        with get_db() as db:
            req = ServiceRequest(**payload, status="pending")
            db.add(req)
            db.flush()
            result = req.to_dict()
        return {"ok": True, "data": result}

    local_req = ServiceRequest(**payload, status="pending")
    with get_db() as db:
        db.add(local_req)
        db.flush()
        local_id = local_req.id

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{main_server_url}/api/service-bridge/requests", json=payload)
            resp.raise_for_status()
            remote_data = resp.json().get("data", {})

        with get_db() as db:
            req = db.query(ServiceRequest).filter(ServiceRequest.id == local_id).first()
            if req:
                req.extra_data = json.dumps({"remote_id": remote_data.get("id"), "synced": True})
                db.flush()
                result = req.to_dict()
        return {"ok": True, "data": result, "remote_id": remote_data.get("id")}
    except httpx.ConnectError:
        with get_db() as db:
            req = db.query(ServiceRequest).filter(ServiceRequest.id == local_id).first()
            if req:
                req.extra_data = json.dumps({"synced": False, "error": "connection_failed"})
                db.flush()
                result = req.to_dict()
        return {"ok": False, "data": result, "error": "无法连接到主服务器"}
    except Exception as e:
        logger.error("outbox forward failed: %s", e)
        raise HTTPException(status_code=502, detail=f"转发到主服务器失败: {e}") from e


@router.get("/outbox")
async def list_outbox():
    instance_id = _get_or_create_instance_id()
    with get_db() as db:
        from app.db.models.service_request import ServiceRequest

        items = (
            db.query(ServiceRequest)
            .filter(ServiceRequest.source_instance_id == instance_id)
            .order_by(ServiceRequest.created_at.desc())
            .all()
        )
        return {"ok": True, "data": [item.to_dict() for item in items]}


@router.post("/outbox/sync")
async def sync_outbox():
    instance_id = _get_or_create_instance_id()
    main_server_url = (_get_config_value("main_server_url", "") or "").strip().rstrip("/")
    if not main_server_url:
        return {"ok": True, "synced_count": 0}

    synced_count = 0
    with get_db() as db:
        from app.db.models.service_request import ServiceRequest

        for req in (
            db.query(ServiceRequest).filter(ServiceRequest.source_instance_id == instance_id).all()
        ):
            extra = {}
            try:
                extra = json.loads(req.extra_data) if req.extra_data else {}
            except Exception:
                pass
            remote_id = extra.get("remote_id")
            if not remote_id:
                continue
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"{main_server_url}/api/service-bridge/requests/{remote_id}"
                    )
                    if resp.status_code == 200:
                        remote_data = resp.json().get("data", {})
                        if remote_data.get("response"):
                            req.response = remote_data["response"]
                            req.responded_by = remote_data.get("responded_by")
                            req.status = remote_data.get("status", req.status)
                            synced_count += 1
            except Exception:
                pass
        db.flush()
    return {"ok": True, "synced_count": synced_count}


@router.get("/ping-main")
async def ping_main_server():
    main_server_url = (_get_config_value("main_server_url", "") or "").strip().rstrip("/")
    if not main_server_url:
        return {"ok": True, "connected": True, "main_server": "(本机直写)"}
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{main_server_url}/api/ping")
            resp.raise_for_status()
            return {"ok": True, "connected": True, "main_server": main_server_url}
    except Exception as e:
        return {"ok": False, "connected": False, "main_server": main_server_url, "error": str(e)}
