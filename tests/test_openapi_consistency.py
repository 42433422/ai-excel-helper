# -*- coding: utf-8 -*-
"""
OpenAPI 与实际路由一致性测试（pytest 版）

与 ``scripts/check_openapi_consistency.py`` 共用底层实现，这里只复核 **error 级**
发现，作为 CI 守门员：``warn`` 级（缺 summary/description/响应 schema）不阻塞，
允许逐步补齐。

覆盖问题：
    - 运行时同一 (method, path) 被多个不同 endpoint 注册，相互覆盖
    - OpenAPI 中出现但运行时未注册
    - 运行时可见路由未进入 OpenAPI（非白名单）
    - ``operationId`` 重复

白名单通过默认规则处理（``/openapi.json`` / ``/docs`` / ``/metrics`` / 历史
回退路由 ``/{fallback:path}`` 等）。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"


def _load_checker_module():
    """把 ``scripts/check_openapi_consistency.py`` 作为模块导入。

    由于脚本内部使用了 ``@dataclass``，而 ``dataclasses`` 在处理类时会回查
    ``sys.modules[cls.__module__]``，所以这里必须先把 spec 注册到 ``sys.modules``
    才能触发 ``exec_module``。
    """
    import importlib.util

    mod_name = "_check_openapi_consistency"
    if mod_name in sys.modules:
        return sys.modules[mod_name]

    path = SCRIPTS_DIR / "check_openapi_consistency.py"
    spec = importlib.util.spec_from_file_location(mod_name, str(path))
    assert spec and spec.loader, f"无法定位 {path}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        sys.modules.pop(mod_name, None)
        raise
    return mod


def test_openapi_and_routes_are_consistent():
    """生产路由与 OpenAPI schema 必须一致（无 error 级发现）。"""
    os.environ.setdefault("XCAGI_NEURO_INTENT", "1")
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    checker = _load_checker_module()

    from app.fastapi_app import get_fastapi_app

    app = get_fastapi_app()

    routes = checker.collect_runtime_routes(app)
    ops, _schema = checker.collect_openapi_operations(app)

    ignores = checker._compile_ignores(list(checker._DEFAULT_IGNORE_PATTERNS))

    findings = []
    findings.extend(checker.diff_routes_vs_openapi(routes, ops, ignores))
    findings.extend(checker.check_operation_quality(ops))

    errors = [f for f in findings if f.level == "error"]

    if errors:
        # 组装易读的断言消息
        lines = [
            f"发现 {len(errors)} 条 OpenAPI/路由一致性 error（warn/info 不计）：",
        ]
        for f in errors[:20]:
            where = f" {f.method} {f.path}" if f.path else ""
            lines.append(f"  [{f.code}]{where}  {f.message}")
        if len(errors) > 20:
            lines.append(
                f"  … 还有 {len(errors) - 20} 条，运行 "
                "``python scripts/check_openapi_consistency.py`` 查看完整列表。"
            )
        raise AssertionError("\n".join(lines))


def test_openapi_schema_builds_without_pydantic_errors():
    """``app.openapi()`` 必须能生成完整 schema（无 PydanticUserError / ForwardRef 未解析等）。

    这条测试针对的是 ``from __future__ import annotations`` + 装饰器包装路由
    （例如 ``@publish_route_event``）导致 FastAPI 把 BaseModel 退化为 Query 参数，
    进而在 OpenAPI 生成时抛 ``PydanticUserError`` 的典型场景。
    """
    os.environ.setdefault("XCAGI_NEURO_INTENT", "1")
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

    from app.fastapi_app import get_fastapi_app

    app = get_fastapi_app()

    schema = app.openapi()
    assert isinstance(schema, dict)
    assert schema.get("paths"), "OpenAPI schema 必须包含非空 paths"
    assert "/api/health" in (schema.get("paths") or {}), "健康检查端点必须在 OpenAPI 中可见"
