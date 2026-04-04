"""
Mod System Infrastructure

提供 Mod 模块的加载、管理、注册能力。
"""

from .manifest import ModMetadata, parse_manifest, validate_dependencies
from .registry import ModRegistry, get_mod_registry
from .base import Mod
from .comms import (
    ModCommsConflictError,
    ModCommsError,
    ModCommsNotFoundError,
    ModCommsRegistry,
    get_caller_mod_id,
    get_mod_comms,
)

__all__ = [
    "ModMetadata",
    "parse_manifest",
    "validate_dependencies",
    "ModRegistry",
    "get_mod_registry",
    "Mod",
    "ModCommsRegistry",
    "ModCommsError",
    "ModCommsNotFoundError",
    "ModCommsConflictError",
    "get_mod_comms",
    "get_caller_mod_id",
]