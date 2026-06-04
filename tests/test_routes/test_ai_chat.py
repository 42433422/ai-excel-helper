# -*- coding: utf-8 -*-
"""AI 聊天/意图路由冒烟（FastAPI 版）。

历史：
    原文件约 1160 行，基于 Flask ``test_client`` 与 ``mock AI service``
    断言 100+ 行为。Flask → FastAPI 迁移完成后 fixture 已无法启动应用，
    整个文件处于"死测试"状态。

    重写后保留骨干思路：
    - ``/api/ai/test`` 健康探针
    - ``/api/ai/intent/test`` 意图识别（mock 掉 ``recognize_intents``）
    - ``/api/ai/chat-unified`` / ``/api/ai/chat-unified/batch``
      （mock 掉 ``unified_chat_single_payload``）

    这三条在 Phase 2A/2C 之后分别落在:
    - ``/api/ai/test`` → :mod:`app.fastapi_routes.ai_intent`
    - ``/api/ai/intent/test`` → :mod:`app.fastapi_routes.ai_intent`
    - ``/api/ai/chat-unified`` / ``batch`` → :mod:`app.fastapi_routes.ai_intent`

    Domain 层真正的 ``/api/ai/chat`` 在 ``app.fastapi_routes.xcagi_compat`` 中、
    需要 DB 与 p2 鉴权,不适合在此做冒烟,交给整机集成测试覆盖。
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.fastapi_routes import ai_intent, legacy_gaps_batch1, legacy_gaps_batch2


@pytest.fixture
def app_with_routers() -> FastAPI:
    app = FastAPI()
    app.include_router(ai_intent.router)
    app.include_router(legacy_gaps_batch1.router)
    app.include_router(legacy_gaps_batch2.router)
    return app


@pytest.fixture
def client(app_with_routers: FastAPI) -> TestClient:
    with TestClient(app_with_routers, raise_server_exceptions=False) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /api/ai/test
# ---------------------------------------------------------------------------


def test_ai_test_endpoint(client: TestClient) -> None:
    r = client.get("/api/ai/test")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert "message" in body
    assert "timestamp" in body


# ---------------------------------------------------------------------------
# POST /api/ai/intent/test
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_recognize_intents(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    fake = MagicMock(
        return_value={
            "primary_intent": "shipment_generate",
            "tool_key": "shipment_generate",
            "is_greeting": False,
            "intent_hints": ["生成发货单"],
        }
    )
    monkeypatch.setattr("app.routes.ai_chat.recognize_intents", fake)
    return fake


def test_intent_test_success(client: TestClient, mock_recognize_intents: MagicMock) -> None:
    r = client.post("/api/ai/intent/test", json={"message": "生成发货单"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["primary_intent"] == "shipment_generate"
    assert body["data"]["tool_key"] == "shipment_generate"


def test_intent_test_empty_message(client: TestClient) -> None:
    r = client.post("/api/ai/intent/test", json={"message": ""})
    assert r.status_code == 400
    body = r.json()
    assert body["success"] is False
    assert "消息内容不能为空" in body["message"]


def test_intent_test_missing_message(client: TestClient) -> None:
    r = client.post("/api/ai/intent/test", json={})
    assert r.status_code == 400
    assert r.json()["success"] is False


def test_intent_test_recognizer_raises(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.routes.ai_chat.recognize_intents",
        MagicMock(side_effect=Exception("意图识别错误")),
    )
    r = client.post("/api/ai/intent/test", json={"message": "测试"})
    assert r.status_code == 500
    body = r.json()
    assert body["success"] is False
    assert "意图识别失败" in body["message"]


# ---------------------------------------------------------------------------
# POST /api/ai/chat-unified
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_chat_single(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    fake = MagicMock(
        return_value={
            "success": True,
            "message": "处理完成",
            "data": {"text": "测试回复", "action": "ai_response", "data": {}},
            "response": "测试回复",
        }
    )
    monkeypatch.setattr("app.routes.ai_chat.unified_chat_single_payload", fake)
    return fake


def test_chat_unified_success(client: TestClient, mock_chat_single: MagicMock) -> None:
    r = client.post("/api/ai/chat-unified", json={"message": "你好"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["text"] == "测试回复"


def test_chat_unified_passes_user_id_and_source(
    client: TestClient, mock_chat_single: MagicMock
) -> None:
    r = client.post(
        "/api/ai/chat-unified",
        json={"message": "你好", "user_id": "u123", "source": "PRO"},
    )
    assert r.status_code == 200
    args = mock_chat_single.call_args.args
    assert args[0] == "你好"
    assert args[1] == "u123"
    assert args[3] == "pro"


def test_chat_unified_empty_message(client: TestClient) -> None:
    r = client.post("/api/ai/chat-unified", json={"message": ""})
    assert r.status_code == 400
    body = r.json()
    assert body["success"] is False
    assert "消息内容不能为空" in body["message"]


def test_chat_unified_missing_message(client: TestClient) -> None:
    r = client.post("/api/ai/chat-unified", json={})
    assert r.status_code == 400
    assert r.json()["success"] is False


def test_chat_unified_respects_explicit_http_status(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.routes.ai_chat.unified_chat_single_payload",
        MagicMock(
            return_value={
                "success": False,
                "message": "AI 服务错误",
                "_http_status": 500,
            }
        ),
    )
    r = client.post("/api/ai/chat-unified", json={"message": "测试"})
    assert r.status_code == 500
    assert r.json()["success"] is False


def test_chat_unified_get_is_not_allowed(client: TestClient) -> None:
    r = client.get("/api/ai/chat-unified")
    assert r.status_code in (404, 405)


# ---------------------------------------------------------------------------
# POST /api/ai/chat-unified/batch
# ---------------------------------------------------------------------------


def test_chat_unified_batch_empty(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.routes.ai_chat.normalize_batch_messages_payload",
        MagicMock(return_value=[]),
    )
    r = client.post("/api/ai/chat-unified/batch", json={"messages": []})
    assert r.status_code == 400
    assert r.json()["success"] is False


def test_chat_unified_batch_too_many(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.routes.ai_chat.normalize_batch_messages_payload",
        MagicMock(return_value=[f"m{i}" for i in range(25)]),
    )
    r = client.post("/api/ai/chat-unified/batch", json={"messages": ["x"] * 25})
    assert r.status_code == 400
    assert "最多 20 条" in r.json()["message"]


def test_chat_unified_batch_success(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.routes.ai_chat.normalize_batch_messages_payload",
        MagicMock(return_value=["a", "b", "c"]),
    )
    monkeypatch.setattr(
        "app.routes.ai_chat.unified_chat_single_payload",
        MagicMock(
            side_effect=lambda *a, **kw: {
                "success": True,
                "data": {"text": f"reply-{a[0]}"},
            }
        ),
    )
    r = client.post("/api/ai/chat-unified/batch", json={"messages": ["a", "b", "c"]})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["batch"] is True
    assert body["count"] == 3
    assert [item["data"]["text"] for item in body["results"]] == [
        "reply-a",
        "reply-b",
        "reply-c",
    ]


# ---------------------------------------------------------------------------
# Response format
# ---------------------------------------------------------------------------


def test_ai_test_response_is_json(client: TestClient) -> None:
    r = client.get("/api/ai/test")
    assert "application/json" in r.headers.get("content-type", "")
    body = r.json()
    assert isinstance(body, dict)
    assert "success" in body
