# -*- coding: utf-8 -*-
"""
任务上下文服务：维护用户当前结构化任务状态，支持多轮补齐。

此模块已迁移到 app/utils/
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional


class TaskContextService:
    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}
        self._last_customers: Dict[str, Dict[str, Any]] = {}

    def get(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self._store.get(user_id)

    def set(self, user_id: str, plan: Dict[str, Any]) -> None:
        payload = dict(plan or {})
        payload["updated_at"] = time.time()
        self._store[user_id] = payload

    def clear(self, user_id: str) -> None:
        self._store.pop(user_id, None)

    def set_last_customer(self, user_id: str, customer_data: Dict[str, Any]) -> None:
        payload = dict(customer_data or {})
        payload["updated_at"] = time.time()
        self._last_customers[user_id] = payload

    def get_last_customer(self, user_id: str) -> Optional[Dict[str, Any]]:
        return self._last_customers.get(user_id)

    def cleanup(self, max_age_seconds: int = 1800) -> int:
        now = time.time()
        expired = []
        for uid, item in self._store.items():
            if now - float(item.get("updated_at", 0)) > max_age_seconds:
                expired.append(uid)
        for uid in expired:
            self._store.pop(uid, None)

        expired_customers = []
        for uid, item in self._last_customers.items():
            if now - float(item.get("updated_at", 0)) > max_age_seconds:
                expired_customers.append(uid)
        for uid in expired_customers:
            self._last_customers.pop(uid, None)

        return len(expired) + len(expired_customers)


_task_context_service: Optional[TaskContextService] = None


def get_task_context_service() -> TaskContextService:
    global _task_context_service
    if _task_context_service is None:
        _task_context_service = TaskContextService()
    return _task_context_service
