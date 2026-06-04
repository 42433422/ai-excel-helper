# -*- coding: utf-8 -*-
"""
pytest 配置与 fixtures（FastAPI 版）

历史沿革：
    仓库早期为 Flask，`app` / `client` 曾基于 ``flask.Flask.test_client``。
    Flask → FastAPI 迁移完成后（入口：``app.fastapi_app:get_fastapi_app``），
    `app/__init__.py` 退化为 deprecated stub，原 `from app import create_app`
    已不可用，Flask 风格的 fixture 随之失效。

    当前文件以 ``fastapi.testclient.TestClient`` 重建 `app` / `client` fixture，
    并保留无关 web 框架的数据工厂（sample_data_factory 等），使 ``tests/`` 下
    既有测试能够被 pytest 收集并运行。
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# 遗留脚本或尚未对齐 FastAPI 的用例，避免阻塞 CI（见 docs/reports/COVERAGE_RAMP.md）
collect_ignore = [
    "test_intent.py",
    "test_application/test_app_services.py",
    "neuro/test_routing_policy.py",
    "test_coverage_ramp_phase41_routes.py",
    "test_legacy_auth_account_kind.py",
    "test_routes/test_ai_chat.py",
]

# CI 稳定子集：仅跑已验证可在 Linux/Windows 无顺序污染的用例（见 .github/workflows/*.yml）
_CI_STABLE_NODEID_FRAGMENTS = (
    "test_neuro_bus_reliability_env",
    "test_coverage_ramp_routes",
    "test_infrastructure_repositories",
    "test_middleware_rate_limit",
    "test_domain/test_shipment_aggregates",
    "test_wechat_tasks",
    "test_neuro_bus_core",
    "test_db_read_token",
    "test_utils/test_utils",
    "test_openapi_consistency",
    "test_services/test_shipment_service",
    "test_services/test_intent_service",
    "test_services/test_printer_service",
    "test_application/test_shipment_app_service",
    "test_infrastructure/test_shipment_document_generator",
    "test_routes/test_mods_routes",
    "test_routes/test_health",
    "test_routes/test_smoke",
    "test_routes/test_materials",
    # benchmarks/ 需 DB/完整意图栈，见 intent-benchmark.yml，勿纳入 CI_STABLE_ONLY
)


def pytest_collection_modifyitems(config, items):
    if os.environ.get("CI_STABLE_ONLY", "").strip().lower() not in {"1", "true", "yes", "on"}:
        return
    skip = pytest.mark.skip(reason="CI_STABLE_ONLY：非稳定子集，完整回归请本地 omit 该变量")
    for item in items:
        nodeid = item.nodeid.replace("\\", "/")
        if not any(frag in nodeid for frag in _CI_STABLE_NODEID_FRAGMENTS):
            item.add_marker(skip)


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture(autouse=True)
def _isolate_edition_and_product_sku_env(monkeypatch):
    """
    全量后端测试顺序敏感：其它用例或桌面 product-sku.json 会留下
    XCAGI_PRODUCT_SKU / XCAGI_EDITION，导致 edition/generic/minimal 与 deliverable 断言失败。
    """
    for key in (
        "XCAGI_PRODUCT_SKU",
        "XCAGI_EDITION",
        "XCAGI_GENERIC_EDITION",
        "XCAGI_MINIMAL_EDITION",
        "XCAGI_DEFAULT_EDITION",
        "XCAGI_RESOURCES_DIR",
        "XCAGI_DESKTOP_RESOURCES",
        "XCAGI_STAGED_MODS_DIR",
    ):
        monkeypatch.delenv(key, raising=False)
    # 避免读取安装目录 product-sku.json；各用例仍可用 monkeypatch.setenv("XCAGI_PRODUCT_SKU", ...)
    monkeypatch.setenv(
        "XCAGI_PRODUCT_SKU_FILE",
        os.path.join(PROJECT_ROOT, "tests", "_fixtures", "no-product-sku.json"),
    )


# ---------------------------------------------------------------------------
# FastAPI 应用/客户端 fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def app():
    """FastAPI 应用实例（整机装配，走 ``get_fastapi_app()``）。"""
    os.environ.setdefault("XCAGI_NEURO_INTENT", "1")
    from app.fastapi_app import get_fastapi_app

    return get_fastapi_app()


@pytest.fixture(scope="function")
def client(app):
    """与整机 FastAPI 应用绑定的 ``TestClient``。

    故意不使用 ``with TestClient(...) as c:`` 的上下文管理形式 —— 整机应用
    会触发 lifespan startup（NeuroBus、compat shim 注册等），在单机/CI 环境
    里可能阻塞。已有冒烟测试（``tests/test_neuro_migration_smoke.py``）也
    采用裸 ``TestClient(app)`` 的模式以规避该问题。

    业务路由统一用 ``raise_server_exceptions=False`` 让服务端异常被包装成
    5xx JSON 响应，便于从响应体断言。
    """
    from fastapi.testclient import TestClient

    yield TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# 与 web 框架无关的辅助 fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_external_api():
    """Mock 常见外部 API 客户端。"""
    mocks = {
        "httpx": MagicMock(),
        "redis": MagicMock(),
        "wechat": MagicMock(),
    }

    with patch("httpx.AsyncClient", mocks["httpx"]), patch("redis.Redis", mocks["redis"]):
        yield mocks


@pytest.fixture
def mock_file_system():
    """Mock 常见文件系统操作（并提供临时目录）。"""
    temp_dir = tempfile.mkdtemp()

    mocks = {
        "temp_dir": temp_dir,
        "os_path_exists": MagicMock(return_value=True),
        "os_path_join": MagicMock(side_effect=os.path.join),
        "open": MagicMock(),
    }

    with (
        patch("os.path.exists", mocks["os_path_exists"]),
        patch("os.path.join", mocks["os_path_join"]),
        patch("builtins.open", mocks["open"]),
    ):
        yield mocks

    try:
        shutil.rmtree(temp_dir)
    except Exception:
        pass


@pytest.fixture
def sample_data_factory():
    """测试数据工厂 - 生成各种测试数据。"""

    class SampleDataFactory:
        @staticmethod
        def product(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
            data = {
                "product_name": f"测试产品_{SampleDataFactory._random_id()}",
                "price": 99.99,
                "unit": "个",
                "description": "测试描述",
                "category": "测试分类",
                "specification": "测试规格",
            }
            if overrides:
                data.update(overrides)
            return data

        @staticmethod
        def customer(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
            data = {
                "unit_name": f"测试公司_{SampleDataFactory._random_id()}",
                "contact": "张三",
                "phone": "13800138000",
                "address": "测试地址",
                "tax_id": "91310000MA1234567X",
                "bank_info": "测试银行信息",
            }
            if overrides:
                data.update(overrides)
            return data

        @staticmethod
        def shipment(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
            data = {
                "unit_name": f"测试公司_{SampleDataFactory._random_id()}",
                "order_number": f"ORD{SampleDataFactory._random_id()}",
                "products": [
                    {"name": "产品 A", "quantity": 10, "price": 100},
                    {"name": "产品 B", "quantity": 5, "price": 50},
                ],
                "date": "2026-03-17",
                "total_amount": 1250.00,
                "status": "pending",
            }
            if overrides:
                data.update(overrides)
            return data

        @staticmethod
        def wechat_contact(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
            data = {
                "wxid": f"wxid_{SampleDataFactory._random_id()}",
                "nickname": f"测试用户_{SampleDataFactory._random_id()}",
                "remark": "测试备注",
                "phone": "13800138000",
                "type": "friend",
            }
            if overrides:
                data.update(overrides)
            return data

        @staticmethod
        def material(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
            data = {
                "name": f"原材料_{SampleDataFactory._random_id()}",
                "specification": "测试规格",
                "unit": "kg",
                "quantity": 100.0,
                "min_quantity": 10.0,
                "price": 50.0,
            }
            if overrides:
                data.update(overrides)
            return data

        @staticmethod
        def _random_id() -> str:
            import random
            import time

            return f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}"

    return SampleDataFactory


@pytest.fixture
def sample_product() -> dict[str, Any]:
    return {
        "product_name": "测试产品",
        "price": 99.99,
        "unit": "个",
        "description": "测试描述",
    }


@pytest.fixture
def sample_customer() -> dict[str, Any]:
    return {
        "unit_name": "测试公司",
        "contact": "张三",
        "phone": "13800138000",
        "address": "测试地址",
    }


@pytest.fixture
def sample_shipment() -> dict[str, Any]:
    return {
        "unit_name": "测试公司",
        "products": [
            {"name": "产品 A", "quantity": 10, "price": 100},
            {"name": "产品 B", "quantity": 5, "price": 50},
        ],
        "date": "2026-03-17",
    }


@pytest.fixture
def sample_template() -> dict[str, Any]:
    return {
        "name": "测试发货单模板",
        "template_type": "发货单",
        "business_scope": "orders",
        "fields": [
            {"label": "产品型号", "name": "model", "type": "text"},
            {"label": "数量", "name": "quantity", "type": "number"},
            {"label": "单价", "name": "price", "type": "number"},
            {"label": "金额", "name": "amount", "type": "number"},
        ],
        "preview_data": {
            "sample_rows": [{"产品型号": "ABC-001", "数量": 5}],
            "sheet_name": "Sheet1",
        },
    }


@pytest.fixture
def assert_response():
    """针对 httpx ``Response`` 的断言辅助。

    httpx/requests 的响应对象与 Flask 不同：JSON 用 ``.json()`` 而非
    ``.get_json()``；``content_type`` 需从 ``headers["content-type"]`` 读取。
    """

    def assert_success(response, expected_status: int = 200) -> None:
        assert response.status_code == expected_status
        ct = response.headers.get("content-type", "")
        assert "application/json" in ct

    def assert_error(response, expected_status: int = 400) -> None:
        assert response.status_code == expected_status
        ct = response.headers.get("content-type", "")
        assert "application/json" in ct
        data = response.json()
        assert "error" in data or "message" in data

    def assert_json_structure(response, required_fields: list[str]) -> None:
        data = response.json()
        assert isinstance(data, dict)
        for field in required_fields:
            assert field in data, f"缺少必需字段：{field}"

    def assert_list_response(response, key: str = "items") -> None:
        data = response.json()
        assert isinstance(data, dict)
        assert key in data
        assert isinstance(data[key], list)

    return {
        "success": assert_success,
        "error": assert_error,
        "json_structure": assert_json_structure,
        "list": assert_list_response,
    }
