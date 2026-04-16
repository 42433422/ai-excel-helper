"""
从 Mod 的 Flask 蓝图源文件中静态提取 @*.route(...) 装饰的路由（启发式，覆盖常见写法）。
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any


def _route_from_decorator(dec: ast.expr) -> dict[str, Any] | None:
    if not isinstance(dec, ast.Call):
        return None
    func = dec.func
    if not isinstance(func, ast.Attribute):
        return None
    if func.attr != "route":
        return None
    path = ""
    if dec.args:
        a0 = dec.args[0]
        if isinstance(a0, ast.Constant) and isinstance(a0.value, str):
            path = a0.value
        elif isinstance(a0, ast.JoinedStr):
            parts: list[str] = []
            for v in a0.values:
                if isinstance(v, ast.Constant) and isinstance(v.value, str):
                    parts.append(v.value)
                elif isinstance(v, ast.FormattedValue):
                    parts.append("{…}")
            path = "".join(parts) if parts else ""
    methods = ["GET"]
    for kw in dec.keywords:
        if kw.arg != "methods" or kw.value is None:
            continue
        if isinstance(kw.value, (ast.List, ast.Tuple)):
            m: list[str] = []
            for elt in kw.value.elts:
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                    m.append(elt.value.upper())
            if m:
                methods = m
    return {"path": path or "/", "methods": methods}


def scan_flask_route_decorators(py_file: Path) -> list[dict[str, Any]]:
    text = py_file.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(py_file))
    routes: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            info = _route_from_decorator(dec)
            if info:
                routes.append(
                    {
                        "function": node.name,
                        "path": info["path"],
                        "methods": info["methods"],
                    }
                )
    return routes
