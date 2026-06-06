import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration

ENDPOINTS = [
    ("/api/customers/list", "GET", None),
    ("/api/products/list", "GET", None),
    ("/api/shipment/list", "GET", None),
    ("/api/wechat/contacts", "GET", None),
    ("/api/wechat/tasks", "GET", None),
    ("/api/print/printers", "GET", None),
    ("/api/print/default", "GET", None),
    ("/api/print/validate", "GET", None),
    ("/api/ocr/test", "GET", None),
    ("/api/ai/chat", "POST", {"message": "你好"}),
    ("/api/ai/test", "GET", None),
    ("/api/ai/intent/test", "POST", {"message": "生成发货单"}),
]


@pytest.mark.parametrize("path,method,payload", ENDPOINTS)
def test_smoke_endpoint(client: TestClient, path: str, method: str, payload):
    """
    Lightweight smoke tests for main API endpoints.
    Uses the shared `client` fixture from tests/conftest.py (FastAPI TestClient).
    Accepts any non-5xx response (service may return 401/403 for auth-protected endpoints).
    """
    if method == "GET":
        r = client.get(path)
    else:
        r = client.post(path, json=payload)

    assert r.status_code < 500, f"Endpoint {method} {path} returned {r.status_code}: {r.text}"
