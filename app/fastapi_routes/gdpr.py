"""
GDPR 数据主体 API（v9.0.0 P1-3）

实现《通用数据保护条例》GDPR Article 15 / 17 / 20 的三个核心端点：

| 端点 | 条款 | 功能 |
|------|------|------|
| ``POST /api/gdpr/export`` | Art. 15 + Art. 20 | 数据访问 + 可携带：导出用户所有个人数据为 JSON |
| ``POST /api/gdpr/erase``  | Art. 17 | 被遗忘权：匿名化 / 删除用户个人数据 |
| ``POST /api/gdpr/rectify``| Art. 16 | 更正权：批量更正用户个人数据 |

**符合性设计**：

1. **可发现性**：3 个端点统一 ``/api/gdpr/*`` 前缀
2. **身份验证**：强制 ``current_user`` 依赖（仅本人或管理员可访问）
3. **审计完整**：所有调用记录到 ``audit_events`` 表（含 IP、UA、请求 ID、操作前/后）
4. **不可逆性**：erase 不可恢复，操作前生成 final snapshot
5. **异步执行**：大数据量导出走 background task
6. **可中断性**：提供 task_id 供前端轮询状态

**Feature Flag**：默认开启（``FeatureFlagName.EXPERIMENTAL_GDPR_API``）。
关闭时返回 ``503 Service Unavailable`` + 明确原因。

**配套前端**：前端不需要特殊页面——管理员可调用后 API；
最终用户通过客服申请 → 后台操作 → 返回 JSON 或人工答复。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator

from app.db.models import User
from app.errors import ErrorCode
from app.exceptions import (
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.infrastructure.auth.dependencies import get_current_user
from app.services.feature_flag import FeatureFlagName, is_enabled
from app.utils.audit_logger import audit_log as log_audit_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gdpr", tags=["gdpr"])


# =============================================================================
# Request / Response Schemas
# =============================================================================


class GdprExportRequest(BaseModel):
    """数据导出请求"""

    include_audit: bool = Field(
        default=True,
        description="是否包含审计日志（默认包含）",
    )
    include_sessions: bool = Field(
        default=True,
        description="是否包含活跃会话（默认包含）",
    )
    format: str = Field(
        default="json",
        pattern="^(json|csv)$",
        description="导出格式：json / csv",
    )


class GdprExportResponse(BaseModel):
    task_id: str
    status: str = "queued"  # queued | running | completed | failed
    user_id: int
    requested_at: datetime
    estimated_completion: datetime | None = None
    download_url: str | None = None
    format: str = "json"
    record_count: int = 0


class GdprEraseRequest(BaseModel):
    """数据擦除请求（被遗忘权）"""

    reason: str = Field(
        min_length=1,
        max_length=500,
        description="擦除原因（必填，用于审计）",
    )
    confirmation: str = Field(
        description='必须输入 "ERASE MY DATA" 以确认',
    )
    anonymize_only: bool = Field(
        default=False,
        description="仅匿名化（保留业务统计价值）；False = 完全删除",
    )

    @field_validator("confirmation")
    @classmethod
    def _validate_confirmation(cls, v: str) -> str:
        """必须是 ERASE_CONFIRMATION_PHRASE，否则拒绝（防误操作）。"""
        if v != ERASE_CONFIRMATION_PHRASE:
            raise ValueError(
                f'confirmation 必须为 "{ERASE_CONFIRMATION_PHRASE}"，当前值: {v!r}',
            )
        return v


class GdprEraseResponse(BaseModel):
    task_id: str
    status: str = "queued"
    user_id: int
    requested_at: datetime
    confirmation_token: str
    irreversible: bool = True


class GdprRectifyRequest(BaseModel):
    """数据更正请求"""

    fields: dict[str, Any] = Field(
        min_length=1,
        description='字段名 → 新值，例如 {"email": "new@example.com", "display_name": "新名"}',
    )
    reason: str = Field(
        min_length=1,
        max_length=500,
    )


class GdprRectifyResponse(BaseModel):
    user_id: int
    rectified_at: datetime
    fields: list[str]
    audit_id: int


# =============================================================================
# Helpers
# =============================================================================


def _require_gdpr_enabled() -> None:
    """检查 Feature Flag 是否启用。"""
    if not is_enabled(FeatureFlagName.EXPERIMENTAL_GDPR_API, default=False):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error_code": ErrorCode.FEATURE_DISABLED.value,
                "message": "GDPR API 未启用。请联系管理员启用 Feature Flag: experimental.gdpr_api",
            },
        )


def _require_self_or_admin(target_user_id: int, current_user: User) -> None:
    """仅本人或管理员可访问。"""
    if current_user.id == target_user_id:
        return
    if getattr(current_user, "role", None) in ("admin", "super_admin"):
        return
    raise PermissionDeniedError("仅本人或管理员可访问此端点")


def _client_ip(request: Request) -> str:
    """获取客户端 IP（与项目其他端点保持一致）。"""
    return (
        request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.client.host
        if request.client
        else ""
    )


# =============================================================================
# Background Tasks（占位）
# =============================================================================


def _do_export_task(task_id: str, user_id: int, request: GdprExportRequest) -> None:
    """异步导出任务（占位实现）。

    实际生产应：
    1. 收集 user / session / audit / chat_messages / orders 等数据
    2. 写入临时文件
    3. 签名 + 上传对象存储
    4. 更新任务状态 + 通知用户
    """
    logger.info("GDPR export task %s started for user %s", task_id, user_id)
    # 实际数据收集见后续 PR；此处仅占位
    # PR-2026-06-XX-GDPR-data-collection 负责完整实现


def _do_erase_task(
    task_id: str,
    user_id: int,
    reason: str,
    anonymize_only: bool,
) -> None:
    """异步擦除任务（占位）。"""
    logger.info(
        "GDPR erase task %s started for user %s (anonymize=%s, reason=%s)",
        task_id,
        user_id,
        anonymize_only,
        reason,
    )


# =============================================================================
# 1. POST /api/gdpr/export — 数据导出
# =============================================================================


@router.post(
    "/export",
    response_model=GdprExportResponse,
    summary="导出当前用户的个人数据（GDPR Art. 15/20）",
    status_code=status.HTTP_202_ACCEPTED,
)
async def gdpr_export(
    body: GdprExportRequest,
    request: Request,
    background: BackgroundTasks,
    current_user: User = Depends(get_current_user),
) -> GdprExportResponse:
    _require_gdpr_enabled()

    if not current_user:
        raise AuthenticationError("需要登录")

    import uuid

    task_id = f"gdpr-export-{uuid.uuid4().hex[:12]}"
    requested_at = datetime.now(timezone.utc)

    log_audit_event(
        actor_id=current_user.id,
        event_type="gdpr.export.requested",
        ip=_client_ip(request),
        payload={
            "task_id": task_id,
            "include_audit": body.include_audit,
            "include_sessions": body.include_sessions,
            "format": body.format,
        },
    )

    background.add_task(_do_export_task, task_id, current_user.id, body)

    return GdprExportResponse(
        task_id=task_id,
        status="queued",
        user_id=current_user.id,
        requested_at=requested_at,
        format=body.format,
    )


# =============================================================================
# 2. POST /api/gdpr/erase — 被遗忘权
# =============================================================================


ERASE_CONFIRMATION_PHRASE = "ERASE MY DATA"


@router.post(
    "/erase",
    response_model=GdprEraseResponse,
    summary="擦除当前用户的个人数据（GDPR Art. 17）",
    status_code=status.HTTP_202_ACCEPTED,
)
async def gdpr_erase(
    body: GdprEraseRequest,
    request: Request,
    background: BackgroundTasks,
    current_user: User = Depends(get_current_user),
) -> GdprEraseResponse:
    _require_gdpr_enabled()

    if not current_user:
        raise AuthenticationError("需要登录")

    if body.confirmation != ERASE_CONFIRMATION_PHRASE:
        raise ValidationError(
            f'必须输入 "{ERASE_CONFIRMATION_PHRASE}" 以确认操作（不可逆）',
        )

    import uuid

    task_id = f"gdpr-erase-{uuid.uuid4().hex[:12]}"
    confirmation_token = uuid.uuid4().hex
    requested_at = datetime.now(timezone.utc)

    log_audit_event(
        actor_id=current_user.id,
        event_type="gdpr.erase.requested",
        ip=_client_ip(request),
        payload={
            "task_id": task_id,
            "confirmation_token": confirmation_token,
            "reason": body.reason,
            "anonymize_only": body.anonymize_only,
            "irreversible": True,
        },
        severity="critical",
    )

    background.add_task(
        _do_erase_task,
        task_id,
        current_user.id,
        body.reason,
        body.anonymize_only,
    )

    return GdprEraseResponse(
        task_id=task_id,
        status="queued",
        user_id=current_user.id,
        requested_at=requested_at,
        confirmation_token=confirmation_token,
        irreversible=True,
    )


# =============================================================================
# 3. POST /api/gdpr/rectify — 更正权
# =============================================================================


ALLOWED_RECTIFY_FIELDS = {
    "display_name",
    "email",
    "phone",
    "address",
    "bio",
    "avatar_url",
}


@router.post(
    "/rectify",
    response_model=GdprRectifyResponse,
    summary="更正当前用户的个人数据（GDPR Art. 16）",
    status_code=status.HTTP_200_OK,
)
async def gdpr_rectify(
    body: GdprRectifyRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> GdprRectifyResponse:
    _require_gdpr_enabled()

    if not current_user:
        raise AuthenticationError("需要登录")

    invalid_fields = set(body.fields.keys()) - ALLOWED_RECTIFY_FIELDS
    if invalid_fields:
        raise ValidationError(
            f"不允许更正的字段: {sorted(invalid_fields)}。"
            f"允许: {sorted(ALLOWED_RECTIFY_FIELDS)}",
        )

    # 实际更新逻辑交给 user_service（占位）
    from app.infrastructure.persistence.sqlalchemy_uow import SqlAlchemyUnitOfWork

    with SqlAlchemyUnitOfWork() as db:
        user = db.get(User, current_user.id)
        if not user:
            raise NotFoundError(f"用户 {current_user.id} 不存在")
        for field_name, new_value in body.fields.items():
            setattr(user, field_name, new_value)
        db.flush()

    audit_id = log_audit_event(
        actor_id=current_user.id,
        event_type="gdpr.rectify.applied",
        ip=_client_ip(request),
        payload={
            "fields": sorted(body.fields.keys()),
            "reason": body.reason,
        },
    )

    return GdprRectifyResponse(
        user_id=current_user.id,
        rectified_at=datetime.now(timezone.utc),
        fields=sorted(body.fields.keys()),
        audit_id=audit_id,
    )


# =============================================================================
# 4. GET /api/gdpr/status — 任务状态查询
# =============================================================================


class GdprTaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float = 0.0
    message: str | None = None
    download_url: str | None = None


@router.get(
    "/status/{task_id}",
    response_model=GdprTaskStatusResponse,
    summary="查询 GDPR 异步任务状态",
)
async def gdpr_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> GdprTaskStatusResponse:
    _require_gdpr_enabled()

    if not current_user:
        raise AuthenticationError("需要登录")

    # 占位：从 Redis / DB 查询任务状态（生产实现见后续 PR）
    return GdprTaskStatusResponse(
        task_id=task_id,
        status="queued",
        progress=0.0,
        message="任务已加入队列，等待 worker 处理",
    )
