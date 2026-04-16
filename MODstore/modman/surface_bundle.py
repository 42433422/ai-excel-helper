"""加载内置 extension_surface.json（与 setuptools package-data 同路径）。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict


def bundled_extension_surface_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "extension_surface.json"


@lru_cache(maxsize=1)
def load_bundled_extension_surface() -> Dict[str, Any]:
    p = bundled_extension_surface_path()
    if not p.is_file():
        return {"schema_version": 0, "error": f"missing bundled surface: {p}"}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"schema_version": 0, "error": "invalid json root"}
    except (OSError, json.JSONDecodeError) as e:
        return {"schema_version": 0, "error": str(e)}
