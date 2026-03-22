"""
Task Context Service 测试
"""

import pytest
from app.services.task_context_service import get_task_context_service


class TestTaskContextService:
    """任务上下文服务测试"""

    @pytest.fixture
    def service(self):
        svc = get_task_context_service()
        svc.clear("test_user")
        yield svc
        svc.clear("test_user")

    def test_get_empty_context(self, service):
        result = service.get("nonexistent_user")
        assert result is None

    def test_set_and_get_context(self, service):
        task_data = {
            "task_type": "shipment_generate",
            "slots": {"unit_name": "测试单位"}
        }
        service.set("test_user", task_data)
        result = service.get("test_user")
        assert result is not None
        assert result["task_type"] == "shipment_generate"

    def test_delete_context(self, service):
        task_data = {"task_type": "test"}
        service.set("test_user", task_data)
        service.clear("test_user")
        assert service.get("test_user") is None

    def test_get_task_context_service_singleton(self):
        svc1 = get_task_context_service()
        svc2 = get_task_context_service()
        assert svc1 is svc2