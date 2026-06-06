"""
安全域（SafetyNeuroDomain）

安全审计事件：登录异常、权限变更、数据访问
"""

import logging
from typing import Any

from app.neuro_bus.domains.base import DomainChannel, NeuroDomain, get_domain_registry
from app.neuro_bus.events.base import EventPriority
from app.neuro_bus.neuro_trace_config import bump_domain_handler_metric

logger = logging.getLogger(__name__)


class SafetyNeuroDomain(NeuroDomain):
    """
    安全神经域

    事件：
    - security.login.anomaly
    - security.permission.changed
    - security.data.access
    - security.threat.detected
    - security.audit.log
    """

    domain_name = "safety"
    default_channel = DomainChannel.CRITICAL

    def __init__(self, bus=None):
        super().__init__(bus)
        self._threat_count = 0
        self._audit_count = 0
        self._setup_handlers()

    def _setup_handlers(self):
        @self.on("security.threat.detected", priority=0, channel=DomainChannel.CRITICAL)
        async def on_threat(event):
            self._threat_count += 1
            threat_type = event.payload.get("threat_type")
            severity = event.payload.get("severity")
            logger.critical(f"SECURITY THREAT: type={threat_type}, severity={severity}")
            bump_domain_handler_metric("security.threat.detected")

        @self.on("security.audit.log", priority=2, channel=DomainChannel.CRITICAL)
        async def on_audit(event):
            self._audit_count += 1
            action = event.payload.get("action")
            user_id = event.payload.get("user_id")
            logger.info(f"Audit: user={user_id}, action={action}")
            bump_domain_handler_metric("security.audit.log")

    async def initialize(self):
        logger.info("SafetyNeuroDomain initialized")

    async def shutdown(self):
        logger.info("SafetyNeuroDomain shutdown")

    def emit_login_anomaly(
        self,
        user_id: str,
        anomaly_type: str,
        details: dict[str, Any],
    ) -> bool:
        return self.emit(
            "security.login.anomaly",
            priority=EventPriority.HIGH,
            payload={
                "user_id": user_id,
                "anomaly_type": anomaly_type,
                "details": details,
                "timestamp": __import__("time").time(),
            },
        )

    def emit_permission_changed(
        self,
        user_id: str,
        changed_by: str,
        old_roles: list,
        new_roles: list,
    ) -> bool:
        return self.emit(
            "security.permission.changed",
            priority=EventPriority.HIGH,
            payload={
                "user_id": user_id,
                "changed_by": changed_by,
                "old_roles": old_roles,
                "new_roles": new_roles,
            },
        )

    def emit_threat_detected(
        self,
        threat_type: str,
        severity: str,  # "low", "medium", "high", "critical"
        source: str,
        description: str,
    ) -> bool:
        return self.emit(
            "security.threat.detected",
            priority=EventPriority.CRITICAL,
            payload={
                "threat_type": threat_type,
                "severity": severity,
                "source": source,
                "description": description,
            },
        )

    def emit_audit_log(
        self,
        user_id: str,
        action: str,
        resource: str,
        result: str,
        metadata: dict[str, Any] = None,
    ) -> bool:
        return self.emit(
            "security.audit.log",
            priority=EventPriority.NORMAL,
            payload={
                "user_id": user_id,
                "action": action,
                "resource": resource,
                "result": result,
                "metadata": metadata or {},
            },
        )

    def get_stats(self) -> dict[str, Any]:
        base = super().get_stats()
        return {
            **base,
            "threats_detected": self._threat_count,
            "audit_logs": self._audit_count,
        }


_safety_domain: SafetyNeuroDomain | None = None


def get_safety_domain() -> SafetyNeuroDomain:
    global _safety_domain
    if _safety_domain is None:
        _safety_domain = SafetyNeuroDomain()
        get_domain_registry().register(_safety_domain)
    return _safety_domain
