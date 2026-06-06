"""Mod 间通信总线（SDK re-export）。"""

from __future__ import annotations

from app.infrastructure.mods.comms import (  # noqa: F401
    get_caller_mod_id,
    get_mod_comms,
)

__all__ = ["get_caller_mod_id", "get_mod_comms"]
