"""Desktop runtime helpers for XCAGI.

The desktop build keeps the existing FastAPI + Vue contract intact, but swaps
in local defaults before the application imports database/cache modules.
"""

from __future__ import annotations

from .database_profile import (
    load_or_create_profile,
    profile_path,
    redact_database_url,
    resolve_storage_mode,
)
from .paths import (
    configure_desktop_environment,
    ensure_desktop_dirs,
    get_desktop_data_dir,
    get_desktop_mode,
    is_desktop_mode,
)

__all__ = [
    "configure_desktop_environment",
    "ensure_desktop_dirs",
    "get_desktop_data_dir",
    "get_desktop_mode",
    "is_desktop_mode",
    "load_or_create_profile",
    "profile_path",
    "redact_database_url",
    "resolve_storage_mode",
]
