from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func as sql_func

from app.db.base import Base
from app.domain.approval.safe_dsl import should_trigger_condition


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    WITHDRAWN = "withdrawn"


class ApprovalNodeType(str, Enum):
    SERIAL = "serial"
    PARALLEL = "parallel"
    COUNTERSIGN = "countersign"
    OR_SIGN = "or_sign"


class ApprovalAction(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    TRANSFER = "transfer"
    DELEGATE = "delegate"
    WITHDRAW = "withdraw"
    CANCEL = "cancel"


class ApprovalFlow(Base):
    __tablename__ = "approval_flows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flow_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    flow_name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    industry: Mapped[str] = mapped_column(String(64), default="通用")
    business_type: Mapped[str] = mapped_column(String(64), default="general", index=True)

    node_type: Mapped[str] = mapped_column(String(32), default=ApprovalNodeType.SERIAL.value)
    allow_transfer: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_delegate: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_withdraw: Mapped[bool] = mapped_column(Boolean, default=True)
    timeout_hours: Mapped[int] = mapped_column(Integer, default=48)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)

    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=sql_func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=sql_func.now(), onupdate=sql_func.now()
    )

    nodes: Mapped[list[ApprovalFlowNode]] = relationship(
        "ApprovalFlowNode", back_populates="flow", cascade="all, delete-orphan"
    )
    requests: Mapped[list[ApprovalRequest]] = relationship("ApprovalRequest", back_populates="flow")
    creator: Mapped[Optional[User]] = relationship("User", foreign_keys=[created_by])

    __table_args__ = (Index("idx_flow_key_active", "flow_key", "is_active"),)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "flow_key": self.flow_key,
            "flow_name": self.flow_name,
            "description": self.description,
            "industry": self.industry,
            "business_type": self.business_type or "general",
            "node_type": self.node_type,
            "allow_transfer": self.allow_transfer,
            "allow_delegate": self.allow_delegate,
            "allow_withdraw": self.allow_withdraw,
            "timeout_hours": self.timeout_hours,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "nodes": [node.to_dict() for node in self.nodes],
        }


class ApprovalFlowNode(Base):
    __tablename__ = "approval_flow_nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flow_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("approval_flows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_name: Mapped[str] = mapped_column(String(128), nullable=False)
    node_order: Mapped[int] = mapped_column(Integer, nullable=False)

    node_type: Mapped[str] = mapped_column(String(32), default=ApprovalNodeType.SERIAL.value)

    approver_type: Mapped[str] = mapped_column(String(32), nullable=False)
    approver_ids: Mapped[Optional[str]] = mapped_column(Text)
    min_approvals: Mapped[int] = mapped_column(Integer, default=1)

    condition_expression: Mapped[Optional[str]] = mapped_column(Text)
    condition_description: Mapped[Optional[str]] = mapped_column(String(256))

    timeout_hours: Mapped[Optional[int]] = mapped_column(Integer)
    timeout_action: Mapped[str] = mapped_column(String(32), default="notify")

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=sql_func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=sql_func.now(), onupdate=sql_func.now()
    )

    flow: Mapped[ApprovalFlow] = relationship("ApprovalFlow", back_populates="nodes")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "flow_id": self.flow_id,
            "node_name": self.node_name,
            "node_order": self.node_order,
            "node_type": self.node_type,
            "approver_type": self.approver_type,
            "approver_ids": json.loads(self.approver_ids) if self.approver_ids else [],
            "min_approvals": self.min_approvals,
            "condition_expression": self.condition_expression,
            "condition_description": self.condition_description,
            "timeout_hours": self.timeout_hours,
            "timeout_action": self.timeout_action,
            "is_active": self.is_active,
        }

    def should_trigger(self, context: dict) -> bool:
        return should_trigger_condition(self, context)


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_no: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)

    flow_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("approval_flows.id"), nullable=False, index=True
    )
    business_type: Mapped[str] = mapped_column(String(64), nullable=False)
    business_id: Mapped[Optional[int]] = mapped_column(Integer)
    business_data: Mapped[Optional[str]] = mapped_column(Text)

    applicant_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    applicant_name: Mapped[Optional[str]] = mapped_column(String(64))
    applicant_department: Mapped[Optional[str]] = mapped_column(String(64))

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    current_node_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("approval_flow_nodes.id")
    )
    current_node_order: Mapped[int] = mapped_column(Integer, default=1)

    status: Mapped[str] = mapped_column(
        String(32), default=ApprovalStatus.PENDING.value, index=True
    )
    priority: Mapped[str] = mapped_column(String(16), default="normal")

    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=sql_func.now()
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    rejected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expired_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    approved_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    approved_by_name: Mapped[Optional[str]] = mapped_column(String(64))
    rejection_reason: Mapped[Optional[str]] = mapped_column(String(512))

    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=sql_func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=sql_func.now(), onupdate=sql_func.now()
    )

    flow: Mapped[Optional[ApprovalFlow]] = relationship("ApprovalFlow", back_populates="requests")
    applicant: Mapped[Optional[User]] = relationship("User", foreign_keys=[applicant_id])
    current_node: Mapped[Optional[ApprovalFlowNode]] = relationship(
        "ApprovalFlowNode", foreign_keys=[current_node_id]
    )
    records: Mapped[list[ApprovalRecord]] = relationship(
        "ApprovalRecord", back_populates="request", cascade="all, delete-orphan"
    )
    approver: Mapped[Optional[User]] = relationship("User", foreign_keys=[approved_by])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "request_no": self.request_no,
            "flow_id": self.flow_id,
            "flow_name": self.flow.flow_name if self.flow else None,
            "business_type": self.business_type,
            "business_id": self.business_id,
            "business_data": json.loads(self.business_data) if self.business_data else {},
            "applicant_id": self.applicant_id,
            "applicant_name": self.applicant_name,
            "applicant_department": self.applicant_department,
            "title": self.title,
            "description": self.description,
            "current_node_id": self.current_node_id,
            "current_node_order": self.current_node_order,
            "current_node_name": self.current_node.node_name if self.current_node else None,
            "current_approvers": (
                json.loads(self.current_node.approver_ids)
                if self.current_node and self.current_node.approver_ids
                else []
            ),
            "status": self.status,
            "priority": self.priority,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "rejected_at": self.rejected_at.isoformat() if self.rejected_at else None,
            "approved_by": self.approved_by,
            "approved_by_name": self.approved_by_name,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ApprovalRecord(Base):
    __tablename__ = "approval_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("approval_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    node_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("approval_flow_nodes.id"), nullable=False
    )
    node_name: Mapped[Optional[str]] = mapped_column(String(128))
    node_order: Mapped[Optional[int]] = mapped_column(Integer)

    approver_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    approver_name: Mapped[Optional[str]] = mapped_column(String(64))

    action: Mapped[str] = mapped_column(String(32), nullable=False)
    opinion: Mapped[Optional[str]] = mapped_column(Text)
    reject_reason: Mapped[Optional[str]] = mapped_column(String(512))

    transferred_from: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    transferred_to: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    delegate_user: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))

    is_passed: Mapped[bool] = mapped_column(Boolean, default=False)

    action_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=sql_func.now()
    )
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=sql_func.now()
    )

    request: Mapped[ApprovalRequest] = relationship("ApprovalRequest", back_populates="records")
    approver: Mapped[Optional[User]] = relationship("User", foreign_keys=[approver_id])

    __table_args__ = (Index("idx_request_node", "request_id", "node_order"),)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "request_id": self.request_id,
            "node_id": self.node_id,
            "node_name": self.node_name,
            "node_order": self.node_order,
            "approver_id": self.approver_id,
            "approver_name": self.approver_name,
            "action": self.action,
            "opinion": self.opinion,
            "reject_reason": self.reject_reason,
            "is_passed": self.is_passed,
            "action_time": self.action_time.isoformat() if self.action_time else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
        }


class ApprovalDelegation(Base):
    __tablename__ = "approval_delegations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    delegator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    delegate_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )

    flow_ids: Mapped[Optional[str]] = mapped_column(Text)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    reason: Mapped[Optional[str]] = mapped_column(String(512))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=sql_func.now()
    )
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))

    delegator: Mapped[Optional[User]] = relationship("User", foreign_keys=[delegator_id])
    delegate: Mapped[Optional[User]] = relationship("User", foreign_keys=[delegate_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "delegator_id": self.delegator_id,
            "delegator_name": self.delegator.name if self.delegator else None,
            "delegate_id": self.delegate_id,
            "delegate_name": self.delegate.name if self.delegate else None,
            "flow_ids": json.loads(self.flow_ids) if self.flow_ids else [],
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "reason": self.reason,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


from app.db.models.user import User  # noqa: E402
