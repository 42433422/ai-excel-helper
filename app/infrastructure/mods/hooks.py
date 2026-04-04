"""
Mod Hook System - Event subscription and trigger mechanism
"""

import logging
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class HookManager:
    _instance = None

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    @classmethod
    def get_instance(cls) -> "HookManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def subscribe(self, event: str, handler: Callable) -> None:
        if event not in self._subscribers:
            self._subscribers[event] = []
        self._subscribers[event].append(handler)
        logger.debug(f"Hook subscribed: {event} -> {handler.__name__}")

    def unsubscribe(self, event: str, handler: Callable) -> None:
        if event in self._subscribers:
            try:
                self._subscribers[event].remove(handler)
                logger.debug(f"Hook unsubscribed: {event} -> {handler.__name__}")
            except ValueError:
                pass

    def trigger(self, event: str, *args, **kwargs) -> None:
        if event not in self._subscribers:
            return

        for handler in self._subscribers[event]:
            try:
                handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"Hook handler failed: {event} -> {handler.__name__}: {e}")

    def list_subscribers(self, event: str) -> List[str]:
        if event not in self._subscribers:
            return []
        return [h.__name__ for h in self._subscribers[event]]


def get_hook_manager() -> HookManager:
    return HookManager.get_instance()


def subscribe(event: str, handler: Callable) -> None:
    get_hook_manager().subscribe(event, handler)


def trigger(event: str, *args, **kwargs) -> None:
    # 检查前端是否启用了原版模式，如果是则跳过所有 hooks
    try:
        from app.routes.state import read_client_mods_off_state
        if read_client_mods_off_state():
            logger.debug(f"Hook skipped (client_mods_off=True): {event}")
            return
    except Exception:
        pass

    get_hook_manager().trigger(event, *args, **kwargs)