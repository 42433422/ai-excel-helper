"""Intent / chat-unified / ai_test 路由。

Phase 2A 从 :mod:`app.fastapi_routes.archive_gap_batch1` 与
:mod:`app.fastapi_routes.archive_gap_batch2` 拆分而出,URL 保持不变:

- ``GET /api/ai/test``
- ``POST /api/ai/chat-unified`` / ``POST /api/ai/chat-unified/batch``
- ``POST /api/ai/intent/test``
- ``GET /api/intent/health``
- ``POST /api/intent-packages`` / ``PUT /api/intent-packages/{package_id}``
- ``POST /api/intent/predict`` / ``POST /api/intent/predict_batch``

归属理由: 这些是 AI 意图识别与统一聊天入口的面向前端契约,属于
"AI 对话域"的基础能力,与批量路由簿无关。
"""

from __future__ import annotations

import logging
import os
import time

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ai-intent"])


_INTENT_PACKAGES_STATE: dict[str, bool] = {
    "base": True,
    "industry": True,
    "product": True,
    "quantity": True,
    "customer": True,
}


@router.get("/api/ai/test")
def ai_test():
    return {"success": True, "message": "AI 聊天服务运行正常", "timestamp": time.time()}


@router.post("/api/ai/chat-unified")
def ai_chat_unified_alias(request: Request, body: dict = Body(default_factory=dict)):
    from app.routes.ai_chat import unified_chat_single_payload

    message = (body.get("message", "") or "").strip()
    if not message:
        return JSONResponse({"success": False, "message": "消息内容不能为空"}, status_code=400)
    payload = unified_chat_single_payload(
        message,
        body.get("user_id"),
        request.client.host if request.client else "",
        (body.get("source") or "").strip().lower(),
        body.get("mode"),
        body.get("context") or {},
    )
    status = int(payload.pop("_http_status", 200))
    return JSONResponse(payload, status_code=status)


@router.post("/api/ai/chat-unified/batch")
def ai_chat_unified_batch_alias(request: Request, body: dict = Body(default_factory=dict)):
    from app.routes.ai_chat import normalize_batch_messages_payload, unified_chat_single_payload

    messages = normalize_batch_messages_payload(body)
    if not messages:
        return JSONResponse({"success": False, "message": "messages 不能为空"}, status_code=400)
    if len(messages) > 20:
        return JSONResponse({"success": False, "message": "单次批量最多 20 条"}, status_code=400)
    results: list = []
    for msg in messages:
        payload = unified_chat_single_payload(
            msg,
            body.get("user_id"),
            request.client.host if request.client else "",
            (body.get("source") or "").strip().lower(),
            body.get("mode"),
            body.get("context") or {},
        )
        status = int(payload.pop("_http_status", 200))
        if status >= 400:
            payload["_http_status"] = status
        results.append(payload)
    ok = all(bool(r.get("success")) for r in results if isinstance(r, dict))
    return {"success": ok, "results": results, "count": len(results), "batch": True}


@router.post("/api/ai/intent/test")
def ai_intent_test(body: dict = Body(default_factory=dict)):
    from app.routes.ai_chat import recognize_intents

    message = body.get("message", "")
    if not message:
        return JSONResponse({"success": False, "message": "消息内容不能为空"}, status_code=400)
    try:
        return {"success": True, "data": recognize_intents(message)}
    except Exception as e:
        return JSONResponse(
            {"success": False, "message": f"意图识别失败：{str(e)}"}, status_code=500
        )


@router.get("/api/intent/health")
def intent_health():
    try:
        from app.application.facades.intent_facade import BertIntentClassifier

        model_path = os.environ.get("INTENT_MODEL_PATH")
        classifier = (
            BertIntentClassifier(model_path=model_path) if model_path else BertIntentClassifier()
        )
        return {"status": "ok", "model_available": classifier.is_available()}
    except Exception as e:
        logger.error("intent health: %s", e)
        return JSONResponse(
            {"status": "error", "model_available": False, "error": str(e)},
            status_code=500,
        )


@router.post("/api/intent-packages")
def intent_packages_post(body: dict = Body(default_factory=dict)):
    data = body or {}
    package_states = data.get("packages", {})
    for pkg_id, state in package_states.items():
        if pkg_id in _INTENT_PACKAGES_STATE:
            _INTENT_PACKAGES_STATE[pkg_id] = bool(state)
    return {
        "success": True,
        "message": "意图包配置已更新",
        "data": {"packages": _INTENT_PACKAGES_STATE},
    }


@router.put("/api/intent-packages/{package_id}")
def intent_packages_put(package_id: str, body: dict = Body(default_factory=dict)):
    if package_id not in _INTENT_PACKAGES_STATE:
        return JSONResponse(
            {"success": False, "error": f"未知的意图包: {package_id}"}, status_code=404
        )
    data = body or {}
    enabled = data.get("enabled")
    if enabled is not None:
        _INTENT_PACKAGES_STATE[package_id] = bool(enabled)
    return {
        "success": True,
        "data": {"package_id": package_id, "enabled": _INTENT_PACKAGES_STATE[package_id]},
    }


def _bert_intent_classifier():
    from app.application.facades.intent_facade import BertIntentClassifier

    model_path = os.environ.get("INTENT_MODEL_PATH")
    if model_path:
        return BertIntentClassifier(model_path=model_path)
    return BertIntentClassifier()


@router.post("/api/intent/predict")
def intent_predict(body: dict = Body(default_factory=dict)):
    data = body or {}
    text = data.get("text", "")
    if not text:
        return JSONResponse({"error": "text is required"}, status_code=400)
    try:
        classifier = _bert_intent_classifier()
        return classifier.predict(text, return_probs=True)
    except Exception as e:
        logger.error("intent predict: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/intent/predict_batch")
def intent_predict_batch(body: dict = Body(default_factory=dict)):
    data = body or {}
    texts = data.get("texts", [])
    if not texts:
        return JSONResponse({"error": "texts is required"}, status_code=400)
    try:
        classifier = _bert_intent_classifier()
        results = classifier.predict_batch(texts, return_probs=True)
        return {"results": results}
    except Exception as e:
        logger.error("intent predict_batch: %s", e)
        return JSONResponse({"error": str(e)}, status_code=500)
