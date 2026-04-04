"""
WeChat Plugin - Optional integration for wechat-decrypt and wechat_cv.

This module provides optional support for WeChat features without tight coupling to core business logic.
It can be disabled by not having the resources/wechat* directories.

Usage:
    from app.infrastructure.plugins.wechat_plugin import get_wechat_plugin
    plugin = get_wechat_plugin()
    if plugin.is_available():
        plugin.load_decrypt_db(...)
"""

import logging
import os
from typing import Any, Dict, List, Optional

from app.utils.path_utils import get_resource_path

logger = logging.getLogger(__name__)


class WechatPlugin:
    """Optional WeChat plugin for decrypt/cv features."""

    def __init__(self):
        self._available = False
        self._decrypt_path = None
        self._cv_path = None
        self._check_availability()

    def _check_availability(self) -> bool:
        """Check if WeChat resources are present."""
        decrypt_path = get_resource_path("wechat-decrypt")
        cv_path = get_resource_path("wechat_cv")

        self._decrypt_path = decrypt_path if os.path.isdir(decrypt_path) else None
        self._cv_path = cv_path if os.path.isdir(cv_path) else None

        self._available = bool(self._decrypt_path or self._cv_path)
        if self._available:
            logger.info(f"WeChat plugin available. decrypt={bool(self._decrypt_path)}, cv={bool(self._cv_path)}")
        return self._available

    def is_available(self) -> bool:
        """Check if WeChat features are available."""
        return self._available

    def get_decrypt_path(self) -> Optional[str]:
        """Get path to wechat-decrypt resources."""
        return self._decrypt_path

    def get_cv_path(self) -> Optional[str]:
        """Get path to wechat_cv resources."""
        return self._cv_path

    def add_to_sys_path(self) -> bool:
        """Add WeChat paths to sys.path if available."""
        if not self.is_available():
            return False

        import sys

        paths_added = 0
        for p in [self._decrypt_path, self._cv_path]:
            if p and p not in sys.path:
                sys.path.insert(0, p)
                paths_added += 1

        if paths_added > 0:
            logger.debug(f"Added {paths_added} WeChat paths to sys.path")
        return paths_added > 0

    def get_decrypted_db_path(self, db_type: str = "message") -> Optional[str]:
        """Get path to decrypted DB (message or contact)."""
        if not self._decrypt_path:
            return None
        base = os.path.join(self._decrypt_path, "decrypted")
        if db_type == "contact":
            return os.path.join(base, "contact", "contact.db")
        return os.path.join(base, "message", "message_0.db")


_wechat_plugin: Optional[WechatPlugin] = None


def get_wechat_plugin() -> WechatPlugin:
    """Get the WeChat plugin singleton."""
    global _wechat_plugin
    if _wechat_plugin is None:
        _wechat_plugin = WechatPlugin()
    return _wechat_plugin


def is_wechat_available() -> bool:
    """Convenience function for routes/services."""
    return get_wechat_plugin().is_available()
