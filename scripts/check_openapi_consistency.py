#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenAPI 文档与实际路由的一致性验证
====================================

对 FastAPI 应用执行三类检查：

1. **对账差异（Diff）**
   - ``routes_missing_in_openapi``  —— 运行时注册但没有出现在 OpenAPI 中
     （大多是 ``include_in_schema=False`` 的历史兼容路由 / 隐藏端点，
     需要与白名单比对后再判断是否算缺失）。
   - ``openapi_missing_in_routes``  —— OpenAPI 中出现但运行时没有的操作
     （正常情况不应出现；出现即意味着 openapi schema 与路由已失真）。

2. **元数据质量（Metadata）**
   - 缺少 ``tags`` / ``summary`` / ``description`` / 默认响应 schema
   - 重复 ``operationId``（Swagger / 客户端生成工具会冲突）

3. **报告输出（Report）**
   - 控制台打印分级摘要
   - ``--json-out`` 写完整 JSON 报告
   - ``--md-out`` 写 Markdown 报告（便于提 PR / 存档）
   - ``--strict`` 将 warn 也视作失败；默认 error > 0 时退出码非零

用法（仓库根目录）::

    python scripts/check_openapi_consistency.py
    python scripts/check_openapi_consistency.py --json-out scripts/output/openapi_consistency.json
    python scripts/check_openapi_consistency.py --md-out docs/reports/openapi_consistency.md
    python scripts/check_openapi_consistency.py --strict

常见白名单（默认忽略，不算缺失）::

    /openapi.json  /docs  /docs/oauth2-redirect  /redoc  /metrics
    /api/health    /api/ping
    /{fallback:path}   (Vue history 回退)

可通过 ``--ignore-regex`` 追加额外忽略模式（可多次指定）。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _norm_method(m: str) -> str:
    return (m or "").upper()


def _norm_path(p: str) -> str:
    if not p or p == "/":
        return "/"
    return p.rstrip("/") or "/"


# HTTP 方法里文档化检查我们关心的子集（忽略 HEAD/OPTIONS/TRACE）
_DOC_METHODS: frozenset[str] = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})

# 默认白名单：这些端点允许不在 OpenAPI 中出现
_DEFAULT_IGNORE_PATTERNS: tuple[str, ...] = (
    r"^/openapi\.json$",
    r"^/docs(/.*)?$",
    r"^/redoc(/.*)?$",
    r"^/metrics$",
    r"^/\{fallback:path\}$",
    r"^/\{fallback\}$",
)


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------


@dataclass
class RuntimeRoute:
    """描述一个已挂载到 FastAPI 的路由。"""

    method: str
    path: str  # 归一化路径（保留参数名，去掉类型注解）
    raw_path: str  # 原始路径（可能含 ``{x:int}`` 之类）
    include_in_schema: bool
    endpoint_name: str
    endpoint_qualname: str = ""  # ``module.qualname`` 形式，用于区分不同模块的同名函数
    tags: list[str] = field(default_factory=list)
    summary: str = ""
    operation_id: str = ""


@dataclass
class OpenApiOperation:
    """描述 OpenAPI schema 中的一个操作。"""

    method: str
    path: str
    operation_id: str = ""
    summary: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    has_response_schema: bool = False  # 任意 2xx 响应是否定义了 content schema


@dataclass
class Finding:
    """单条发现。"""

    level: str  # "error" | "warn" | "info"
    code: str
    message: str
    method: str = ""
    path: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# 收集运行时路由
# ---------------------------------------------------------------------------


def collect_runtime_routes(app) -> list[RuntimeRoute]:
    from starlette.routing import Mount

    try:
        from fastapi.routing import APIRoute
    except ImportError:  # pragma: no cover - FastAPI 必然提供
        from starlette.routing import APIRoute  # type: ignore[no-redef]

    from app.utils.openapi_path import normalize_path_template

    out: list[RuntimeRoute] = []

    def walk(routes: Iterable[Any], prefix: str = "") -> None:
        for r in routes:
            if isinstance(r, APIRoute):
                raw = prefix + str(r.path)
                norm = _norm_path(normalize_path_template(raw))
                for m in r.methods or ():
                    method = _norm_method(m)
                    if method not in _DOC_METHODS:
                        continue
                    endpoint = getattr(r, "endpoint", None)
                    ep_mod = getattr(endpoint, "__module__", "") or ""
                    ep_qname = (
                        getattr(endpoint, "__qualname__", "")
                        or getattr(endpoint, "__name__", "")
                        or ""
                    )
                    fq = f"{ep_mod}.{ep_qname}" if ep_mod and ep_qname else (ep_qname or ep_mod)
                    out.append(
                        RuntimeRoute(
                            method=method,
                            path=norm,
                            raw_path=raw,
                            include_in_schema=bool(getattr(r, "include_in_schema", True)),
                            endpoint_name=getattr(r, "name", "") or "",
                            endpoint_qualname=fq,
                            tags=list(getattr(r, "tags", None) or []),
                            summary=str(getattr(r, "summary", "") or ""),
                            operation_id=str(getattr(r, "operation_id", "") or ""),
                        )
                    )
            elif isinstance(r, Mount):
                walk(r.routes, prefix + str(r.path).rstrip("/"))

    walk(app.routes)
    return out


# ---------------------------------------------------------------------------
# 收集 OpenAPI 操作
# ---------------------------------------------------------------------------


def collect_openapi_operations(app) -> tuple[list[OpenApiOperation], dict[str, Any]]:
    schema = app.openapi()
    ops: list[OpenApiOperation] = []

    for path, path_item in (schema.get("paths") or {}).items():
        for method, op in (path_item or {}).items():
            method_u = _norm_method(method)
            if method_u not in _DOC_METHODS:
                continue
            if not isinstance(op, dict):
                continue
            responses = op.get("responses") or {}
            has_resp_schema = False
            for code, resp in responses.items():
                if not isinstance(resp, dict):
                    continue
                # 2xx + default 都算
                if not (str(code).startswith("2") or code == "default"):
                    continue
                content = resp.get("content") or {}
                for _, media in content.items():
                    if isinstance(media, dict) and media.get("schema"):
                        has_resp_schema = True
                        break
                if has_resp_schema:
                    break
            ops.append(
                OpenApiOperation(
                    method=method_u,
                    path=_norm_path(path),
                    operation_id=str(op.get("operationId") or ""),
                    summary=str(op.get("summary") or ""),
                    description=str(op.get("description") or ""),
                    tags=list(op.get("tags") or []),
                    has_response_schema=has_resp_schema,
                )
            )
    return ops, schema


# ---------------------------------------------------------------------------
# 比对与告警
# ---------------------------------------------------------------------------


def _compile_ignores(patterns: Iterable[str]) -> list[re.Pattern[str]]:
    return [re.compile(p) for p in patterns]


def _path_matches(path: str, compiled: Iterable[re.Pattern[str]]) -> bool:
    return any(c.search(path) for c in compiled)


def diff_routes_vs_openapi(
    routes: list[RuntimeRoute],
    ops: list[OpenApiOperation],
    ignores: list[re.Pattern[str]],
) -> list[Finding]:
    findings: list[Finding] = []

    # 额外：运行时 (method, path) 重复注册检测。
    # 区分三类：
    #   1) 同一 endpoint 名重复：``@router.get("/x")`` + ``@router.get("/x/")`` 写法，
    #      OpenAPI 中会出现重复 operationId 告警，但处理器一致；标 ``warn``。
    #   2) 不同 endpoint、且 **多于一条可见于 OpenAPI**：真正的跨模块/新旧路由冲突，
    #      后注册者覆盖前者，需立即修复；标 ``error``。
    #   3) 不同 endpoint、只有一条对 OpenAPI 可见：另一条已显式 ``include_in_schema=False``
    #      用作兼容别名；此类覆盖行为是有意为之，标 ``info``。
    seen_runtime: dict[tuple[str, str], list[tuple[str, str, bool]]] = {}
    for r in routes:
        seen_runtime.setdefault((r.method, r.path), []).append(
            (
                r.endpoint_name or "?",
                r.endpoint_qualname or r.endpoint_name or "?",
                bool(r.include_in_schema),
            )
        )
    for (method, path), entries in seen_runtime.items():
        if len(entries) <= 1:
            continue
        if _path_matches(path, ignores):
            continue
        # 用 fq name（module.qualname）区分，避免把不同模块的同名函数误判为"同一处理器重复挂载"。
        unique_names = sorted({fq for _, fq, _ in entries})
        visible_count = sum(1 for _, _, vis in entries if vis)
        if len(unique_names) == 1:
            findings.append(
                Finding(
                    level="warn",
                    code="DUPLICATE_TRAILING_SLASH_ROUTE",
                    message=(
                        f"{method} {path} 被同一处理器注册了 {len(entries)} 次"
                        f"（endpoint: {unique_names[0]}）；建议把多余的尾斜杠变体标记为"
                        " ``include_in_schema=False`` 或改用 FastAPI 默认重定向"
                    ),
                    method=method,
                    path=path,
                    extra={"endpoints": [e[1] for e in entries]},
                )
            )
        elif visible_count >= 2:
            findings.append(
                Finding(
                    level="error",
                    code="DUPLICATE_ROUTE_REGISTRATION",
                    message=(
                        f"同一 {method} {path} 被 {len(unique_names)} 个不同处理器注册"
                        f"（endpoint: {', '.join(unique_names)}）；后注册者会覆盖前者"
                    ),
                    method=method,
                    path=path,
                    extra={
                        "endpoints": unique_names,
                        "visible_count": visible_count,
                    },
                )
            )
        else:
            findings.append(
                Finding(
                    level="info",
                    code="COMPAT_ALIAS_OVERRIDE",
                    message=(
                        f"{method} {path} 存在 {len(unique_names)} 个处理器但只有 1 个进入文档"
                        f"（endpoint: {', '.join(unique_names)}）；多为历史兼容别名，"
                        "后注册者运行时覆盖前者"
                    ),
                    method=method,
                    path=path,
                    extra={"endpoints": unique_names},
                )
            )

    # 只统计希望进入文档的路由（include_in_schema=True）
    schema_visible = {(r.method, r.path) for r in routes if r.include_in_schema}
    op_keys = {(o.method, o.path) for o in ops}

    missing_in_openapi = sorted(schema_visible - op_keys)
    missing_in_routes = sorted(op_keys - schema_visible)

    for method, path in missing_in_openapi:
        if _path_matches(path, ignores):
            continue
        findings.append(
            Finding(
                level="error",
                code="ROUTE_MISSING_IN_OPENAPI",
                message=f"路由已注册但未进入 OpenAPI 文档：{method} {path}",
                method=method,
                path=path,
            )
        )

    for method, path in missing_in_routes:
        if _path_matches(path, ignores):
            continue
        findings.append(
            Finding(
                level="error",
                code="OPENAPI_MISSING_IN_ROUTES",
                message=f"OpenAPI 文档中出现但运行时未注册：{method} {path}",
                method=method,
                path=path,
            )
        )

    # 顺带报告 include_in_schema=False 的路由，作为 info 级信号
    hidden = sorted(
        {(r.method, r.path) for r in routes if not r.include_in_schema and r.method in _DOC_METHODS}
    )
    for method, path in hidden:
        if _path_matches(path, ignores):
            continue
        findings.append(
            Finding(
                level="info",
                code="ROUTE_HIDDEN_FROM_SCHEMA",
                message=f"路由被显式标记为不进入 OpenAPI：{method} {path}",
                method=method,
                path=path,
            )
        )

    return findings


def check_operation_quality(ops: list[OpenApiOperation]) -> list[Finding]:
    findings: list[Finding] = []

    # 1) 重复 operationId
    op_id_map: dict[str, list[tuple[str, str]]] = {}
    for op in ops:
        if not op.operation_id:
            continue
        op_id_map.setdefault(op.operation_id, []).append((op.method, op.path))
    for op_id, uses in op_id_map.items():
        if len(uses) > 1:
            findings.append(
                Finding(
                    level="error",
                    code="DUPLICATE_OPERATION_ID",
                    message=f"operationId 重复：{op_id} 出现在 {len(uses)} 个操作中",
                    extra={"operation_id": op_id, "uses": uses},
                )
            )

    # 2) 元数据缺失（warn）
    for op in ops:
        if not op.tags:
            findings.append(
                Finding(
                    level="warn",
                    code="MISSING_TAGS",
                    message=f"缺少 tags：{op.method} {op.path}",
                    method=op.method,
                    path=op.path,
                )
            )
        if not op.summary:
            findings.append(
                Finding(
                    level="warn",
                    code="MISSING_SUMMARY",
                    message=f"缺少 summary：{op.method} {op.path}",
                    method=op.method,
                    path=op.path,
                )
            )
        if not op.description:
            findings.append(
                Finding(
                    level="warn",
                    code="MISSING_DESCRIPTION",
                    message=f"缺少 description/docstring：{op.method} {op.path}",
                    method=op.method,
                    path=op.path,
                )
            )
        if not op.has_response_schema:
            findings.append(
                Finding(
                    level="warn",
                    code="MISSING_RESPONSE_SCHEMA",
                    message=f"2xx 响应未声明 schema：{op.method} {op.path}",
                    method=op.method,
                    path=op.path,
                )
            )

    return findings


# ---------------------------------------------------------------------------
# 报告格式化
# ---------------------------------------------------------------------------


def _summary_counts(findings: list[Finding]) -> dict[str, int]:
    counts: dict[str, int] = {"error": 0, "warn": 0, "info": 0}
    for f in findings:
        counts[f.level] = counts.get(f.level, 0) + 1
    return counts


def _group_by_code(findings: list[Finding]) -> dict[str, list[Finding]]:
    out: dict[str, list[Finding]] = {}
    for f in findings:
        out.setdefault(f.code, []).append(f)
    return out


def render_markdown_report(
    findings: list[Finding],
    counts_routes: int,
    counts_ops: int,
) -> str:
    counts = _summary_counts(findings)
    grouped = _group_by_code(findings)
    lines: list[str] = []
    lines.append("# OpenAPI 与路由一致性报告")
    lines.append("")
    lines.append(f"- 运行时路由（含隐藏）: **{counts_routes}**")
    lines.append(f"- OpenAPI 操作: **{counts_ops}**")
    lines.append(
        f"- 发现: error **{counts['error']}** / warn **{counts['warn']}** / info **{counts['info']}**"
    )
    lines.append("")

    # 按严重度 → 分组输出
    level_order = ["error", "warn", "info"]
    code_order = sorted(
        grouped.keys(),
        key=lambda c: (
            level_order.index(grouped[c][0].level) if grouped[c][0].level in level_order else 99,
            c,
        ),
    )
    for code in code_order:
        items = grouped[code]
        level = items[0].level
        lines.append(f"## [{level.upper()}] {code}  ({len(items)})")
        lines.append("")
        for f in items[:200]:  # 防止极端情况打爆
            prefix = f"- `{f.method} {f.path}`" if f.path else "- "
            msg = f.message
            lines.append(f"{prefix} — {msg}")
        if len(items) > 200:
            lines.append(f"- … 省略 {len(items) - 200} 条")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------


def _build_app():
    """构建 FastAPI 应用实例，复用 ``route_inventory_diff`` 的同样策略
    （仅触发 ``create_fastapi_app``，不启动 lifespan）。
    """
    root = _repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    # 避免启动期 LAN 门禁 / license 初始化对环境敏感
    os.environ.setdefault("XCAGI_NEURO_INTENT", "1")

    from app.fastapi_app import create_fastapi_app

    return create_fastapi_app(enable_docs=True, enable_cors=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate OpenAPI schema vs actual FastAPI routes.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Write the full JSON report to this path.",
    )
    parser.add_argument(
        "--md-out",
        type=Path,
        default=None,
        help="Write a human-readable Markdown report to this path.",
    )
    parser.add_argument(
        "--ignore-regex",
        action="append",
        default=[],
        help="Additional regex pattern of paths to ignore (may be repeated).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors for exit-code purposes.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-finding console output; only print summary.",
    )
    args = parser.parse_args(argv)

    app = _build_app()

    routes = collect_runtime_routes(app)
    ops, schema = collect_openapi_operations(app)

    ignores = _compile_ignores(list(_DEFAULT_IGNORE_PATTERNS) + list(args.ignore_regex or []))

    findings: list[Finding] = []
    findings.extend(diff_routes_vs_openapi(routes, ops, ignores))
    findings.extend(check_operation_quality(ops))

    counts = _summary_counts(findings)

    # 控制台输出
    if not args.quiet:
        # 只显示 error / warn 摘要，避免噪音过大
        print(f"[check_openapi_consistency] routes={len(routes)} ops={len(ops)}")
        print(
            f"  error={counts.get('error', 0)} "
            f"warn={counts.get('warn', 0)} "
            f"info={counts.get('info', 0)}"
        )
        shown = 0
        limit = 40
        for f in findings:
            if f.level == "info":
                continue
            prefix = f"[{f.level}] {f.code}"
            where = f" {f.method} {f.path}" if f.path else ""
            print(f"  {prefix}{where}  {f.message}")
            shown += 1
            if shown >= limit:
                remaining = sum(1 for x in findings if x.level != "info") - shown
                if remaining > 0:
                    print(f"  … +{remaining} more (see --md-out / --json-out)")
                break

    # JSON 报告
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "summary": {
                "routes_total": len(routes),
                "routes_hidden": sum(1 for r in routes if not r.include_in_schema),
                "openapi_operations_total": len(ops),
                "counts": counts,
            },
            "info": {
                "title": schema.get("info", {}).get("title"),
                "version": schema.get("info", {}).get("version"),
            },
            "findings": [asdict(f) for f in findings],
            "routes": [asdict(r) for r in routes],
            "openapi_operations": [asdict(o) for o in ops],
        }
        args.json_out.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"Wrote JSON report to {args.json_out}", file=sys.stderr)

    # Markdown 报告
    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        md = render_markdown_report(findings, counts_routes=len(routes), counts_ops=len(ops))
        args.md_out.write_text(md, encoding="utf-8")
        print(f"Wrote Markdown report to {args.md_out}", file=sys.stderr)

    # 退出码
    failed = counts.get("error", 0) > 0 or (args.strict and counts.get("warn", 0) > 0)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
