"""意图识别应用层入口（路由仅依赖 application，不直连 services）。"""

from __future__ import annotations

from typing import Any


def recognize_intents(message: str) -> dict[str, Any]:
    from app.services.intent_service import recognize_intents as _recognize

    return _recognize(message)
