#!/usr/bin/env python3
"""
Architecture Fitness Function

Validates architectural invariants that should hold true across all commits.
Run: python scripts/arch_fitness.py
Exit code: 0 = all checks pass, 1 = violations found
"""

import ast
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = REPO_ROOT / "app"
MODSTORE_SERVER_DIR = Path(r"e:\成都修茈科技有限公司\MODstore_deploy\modstore_server")

MAX_FILE_LINES = 500
BASELINE_FILE = Path(__file__).resolve().parent / "arch_fitness_baseline.txt"

VIOLATIONS: list[str] = []


def _violation_key(violation: str) -> str:
    """基线键：`[check-type] path`（不含行号与行数后缀）。"""
    key = violation.split(" — ", 1)[0].strip() if " — " in violation else violation.strip()
    if "] " in key:
        prefix, path_part = key.split("] ", 1)
        path_part = path_part.replace("\\", "/")
        return f"{prefix}] {path_part}"
    return key.replace("\\", "/")


def _load_baseline_keys() -> set[str]:
    if not BASELINE_FILE.is_file():
        return set()
    keys: set[str] = set()
    for raw in BASELINE_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        keys.add(_violation_key(line))
    return keys


def _is_excluded_path(path: Path) -> bool:
    parts = path.parts
    if "__pycache__" in parts:
        return True
    if any(".v1_backup" in p for p in parts):
        return True
    name = path.name
    if name.startswith("test_") or name.endswith("_test.py"):
        return True
    return False


def _count_lines(path: Path) -> int:
    try:
        return sum(1 for _ in path.open(encoding="utf-8", errors="replace"))
    except (OSError, UnicodeDecodeError):
        return 0


def check_no_v1_backup_files() -> None:
    for path in APP_DIR.rglob("*.v1_backup"):
        rel = path.relative_to(REPO_ROOT)
        VIOLATIONS.append(f"[v1_backup] {rel} — backup file must be removed")


def check_routes_not_import_services() -> None:
    routes_dirs = [APP_DIR / "routes", APP_DIR / "fastapi_routes"]
    for routes_dir in routes_dirs:
        if not routes_dir.is_dir():
            continue
        for py in routes_dir.rglob("*.py"):
            rel = py.relative_to(REPO_ROOT)
            try:
                tree = ast.parse(py.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom):
                    continue
                if node.module and "app.services" in node.module:
                    names = ", ".join(a.name for a in node.names)
                    VIOLATIONS.append(
                        f"[routes->services] {rel}:{node.lineno} — "
                        f"from {node.module} import {names} "
                        f"(routes should use app.application, not app.services)"
                    )


def check_domain_not_depend_on_infrastructure() -> None:
    domain_dir = APP_DIR / "domain"
    if not domain_dir.is_dir():
        return
    for py in domain_dir.rglob("*.py"):
        rel = py.relative_to(REPO_ROOT)
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module and "app.infrastructure" in node.module:
                names = ", ".join(a.name for a in node.names)
                VIOLATIONS.append(
                    f"[domain->infrastructure] {rel}:{node.lineno} — "
                    f"from {node.module} import {names} "
                    f"(domain must not depend on infrastructure)"
                )


def check_no_giant_files_in_app() -> None:
    if not APP_DIR.is_dir():
        return
    for py in APP_DIR.rglob("*.py"):
        if _is_excluded_path(py):
            continue
        line_count = _count_lines(py)
        if line_count > MAX_FILE_LINES:
            rel = py.relative_to(REPO_ROOT)
            VIOLATIONS.append(
                f"[giant-file] {rel} — {line_count} lines " f"(max {MAX_FILE_LINES} in app/)"
            )


def check_no_giant_files_in_modstore_server() -> None:
    if not MODSTORE_SERVER_DIR.is_dir():
        print(f"  [skip] modstore_server not found at {MODSTORE_SERVER_DIR}")
        return
    for py in MODSTORE_SERVER_DIR.rglob("*.py"):
        if _is_excluded_path(py):
            continue
        line_count = _count_lines(py)
        if line_count > MAX_FILE_LINES:
            rel = py.relative_to(MODSTORE_SERVER_DIR.parent)
            VIOLATIONS.append(
                f"[giant-file] {rel} — {line_count} lines "
                f"(max {MAX_FILE_LINES} in modstore_server/)"
            )


def main() -> int:
    print("=== Architecture Fitness Check ===\n")

    check_no_v1_backup_files()
    check_routes_not_import_services()
    check_domain_not_depend_on_infrastructure()
    check_no_giant_files_in_app()
    check_no_giant_files_in_modstore_server()

    baseline = _load_baseline_keys()
    new_violations = [v for v in VIOLATIONS if _violation_key(v) not in baseline]
    baselined = len(VIOLATIONS) - len(new_violations)

    if baselined:
        print(
            f"  [baseline] {baselined} known violation(s) suppressed (see arch_fitness_baseline.txt)"
        )

    if new_violations:
        print(f"FAIL {len(new_violations)} new violation(s) (total found {len(VIOLATIONS)}):\n")
        for v in new_violations:
            print(f"  {v}")
        print()
        return 1

    if VIOLATIONS:
        print("PASS: no new violations (baseline only).")
        return 0

    print("PASS: all architecture fitness checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
