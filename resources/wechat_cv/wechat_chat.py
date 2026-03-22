# -*- coding: utf-8 -*-
"""
微信端聊天入口：基于 AI助手 的 intent_layer + app_api 薄封装。

用法：
  - 仅意图（不连后端）：wechat_intent("你好")  → 意图 + 快捷回复
  - 完整聊天（推荐连后端）：wechat_chat("生成发货单", api_base_url="http://127.0.0.1:5000")
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Optional

# 确保可导入 AI助手 下的 wechat_chat_bridge
_AI_DIR = os.path.join(os.path.dirname(__file__), "..", "AI助手")
if os.path.isdir(_AI_DIR) and _AI_DIR not in sys.path:
    sys.path.insert(0, os.path.dirname(_AI_DIR))

_bridge = None


def _get_bridge():
    global _bridge
    if _bridge is not None:
        return _bridge
    try:
        from AI助手.wechat_chat_bridge import wechat_intent as _wi, wechat_chat as _wc
        _bridge = (_wi, _wc)
        return _bridge
    except Exception:
        pass
    try:
        from wechat_chat_bridge import wechat_intent as _wi, wechat_chat as _wc
        _bridge = (_wi, _wc)
        return _bridge
    except Exception:
        pass
    return None


def wechat_intent(message: str) -> Dict[str, Any]:
    """
    仅意图识别 + 快捷回复建议（不请求后端）。
    依赖 AI助手/intent_layer；若未安装则返回简单兜底。
    """
    bridge = _get_bridge()
    if bridge:
        return bridge[0](message or "")
    return {
        "primary_intent": None,
        "tool_key": None,
        "intent_hints": [],
        "is_negated": False,
        "is_greeting": False,
        "is_goodbye": False,
        "is_help": False,
        "is_likely_unclear": True,
        "quick_reply": "请在本机打开发货单助手后，再说：生成发货单、打印、上传 等。",
    }


def wechat_chat(
    message: str,
    api_base_url: Optional[str] = None,
    session_id: Optional[str] = None,
    source: str = "wechat",
    timeout: int = 30,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    微信统一聊天：优先 POST 到后端 /api/ai/chat，失败则用意图层快捷回复。

    Returns:
        success, text（发回微信的正文）, action, tool_call, intent, data, raw
    """
    bridge = _get_bridge()
    if bridge:
        return bridge[1](
            message or "",
            api_base_url=api_base_url,
            session_id=session_id,
            source=source,
            timeout=timeout,
            **kwargs,
        )
    # 无 bridge 时仅 HTTP 调用
    if api_base_url:
        try:
            import urllib.request
            url = api_base_url.rstrip("/") + "/api/ai/chat"
            body = {
                "message": (message or "").strip(),
                "source": source,
                "session_id": session_id or "",
                "output_format": "markdown",
                **kwargs,
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    payload = json.loads(resp.read().decode("utf-8"))
                    return _normalize(payload)
        except Exception:
            pass
    # 回退
    intent = wechat_intent(message or "")
    return {
        "success": True,
        "text": intent.get("quick_reply") or "您可以说：生成发货单、打印、上传文件、查看模板 等。",
        "action": None,
        "tool_call": None,
        "intent": intent.get("primary_intent") or intent.get("tool_key"),
        "data": intent,
        "raw": None,
    }


def _normalize(api_payload: Dict[str, Any]) -> Dict[str, Any]:
    text = api_payload.get("response") or api_payload.get("message") or "已收到。"
    return {
        "success": bool(api_payload.get("success", True)),
        "text": text,
        "action": api_payload.get("autoAction") or api_payload.get("auto_action"),
        "tool_call": api_payload.get("toolCall") or api_payload.get("tool_call"),
        "intent": api_payload.get("policy_hit") or api_payload.get("primary_intent"),
        "data": api_payload.get("data"),
        "raw": api_payload,
    }


if __name__ == "__main__":
    import sys as _sys
    msg = _sys.argv[1] if len(_sys.argv) > 1 else "你好"
    use_api = "--api" in _sys.argv
    base = "http://127.0.0.1:5000" if use_api else None
    if use_api:
        print(json.dumps(wechat_chat(msg, api_base_url=base), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(wechat_intent(msg), ensure_ascii=False, indent=2))
