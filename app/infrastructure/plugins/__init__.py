"""
Infrastructure plugins for optional features.

Contains:
- wechat_plugin: Optional WeChat decrypt/cv integration
"""

from .wechat_plugin import (
    WechatPlugin,
    get_wechat_plugin,
    is_wechat_available,
)

__all__ = [
    "WechatPlugin",
    "get_wechat_plugin",
    "is_wechat_available",
]
