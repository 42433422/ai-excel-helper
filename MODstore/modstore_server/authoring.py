"""制作向导：合并宿主 OpenAPI 路径摘要。"""

from __future__ import annotations

from typing import Any, Dict, List


def slim_openapi_paths(spec: Dict[str, Any], *, max_items: int = 1000) -> List[Dict[str, Any]]:
    paths = spec.get("paths")
    if not isinstance(paths, dict):
        return []
    out: List[Dict[str, Any]] = []
    for path, ops in paths.items():
        if not isinstance(path, str) or not path.startswith("/api"):
            continue
        if not isinstance(ops, dict):
            continue
        methods = [
            m.upper()
            for m in ops
            if isinstance(m, str) and m.lower() in ("get", "post", "put", "delete", "patch", "head", "options")
        ]
        if methods:
            out.append({"path": path, "methods": sorted(set(methods))})
    out.sort(key=lambda x: x["path"])
    return out[:max_items]
