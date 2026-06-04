# -*- coding: utf-8 -*-
"""
检查 Mod 侧代码对主程的 import 是否只走 ``app.mod_sdk.*`` 契约层。

命中规则
--------

扫描以下路径下的所有 ``.py``::

    mods/**/*.py
    XCAGI/mods/**/*.py

允许的跨边界 import：

- ``app.mod_sdk`` / ``app.mod_sdk.<任意子模块>``
- 其它所有 ``app.*`` 视为违规(``backend/`` 已于 2026-04-20 下线,不再出现)

本脚本纯 AST 静态分析，不执行 Mod 代码；零依赖。
CI / 冒烟脚本里建议当作一个独立 step 跑。
退出码：存在违规时为 ``1``；否则 ``0``。

用法：

    python scripts/dev/check_mod_import_boundaries.py
    python scripts/dev/check_mod_import_boundaries.py --json

"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

# 被扫描的 Mod 代码根目录（相对仓库根）
MOD_ROOTS = (
    Path("mods"),
    Path("XCAGI") / "mods",
)

# 允许跨边界导入的前缀（严格匹配起始 token）
ALLOWED_PREFIXES = ("app.mod_sdk",)

# 视为违规的前缀
FORBIDDEN_PREFIXES = (
    "app",
    # "backend" 目录已于 2026-04-20 下线;Mod 侧新增文件时不得再出现该前缀。
    # 此处仍保留以便捕捉历史残留的非法引用。
    "backend",
)


class Violation:
    __slots__ = ("file", "lineno", "module", "names")

    def __init__(self, file: Path, lineno: int, module: str, names: list[str]) -> None:
        self.file = file
        self.lineno = lineno
        self.module = module
        self.names = names

    def to_dict(self) -> dict:
        return {
            "file": str(self.file).replace("\\", "/"),
            "lineno": self.lineno,
            "module": self.module,
            "names": list(self.names),
        }


def _module_is_allowed(module: str) -> bool:
    """Return True iff ``module`` is OK to import from Mod code."""
    if not module:
        return True
    for ok in ALLOWED_PREFIXES:
        if module == ok or module.startswith(ok + "."):
            return True
    for bad in FORBIDDEN_PREFIXES:
        if module == bad or module.startswith(bad + "."):
            return False
    return True


def _scan_file(path: Path) -> list[Violation]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as e:
        return [Violation(path, e.lineno or 0, "<syntax-error>", [str(e)])]

    violations: list[Violation] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not _module_is_allowed(alias.name):
                    violations.append(
                        Violation(path, node.lineno, alias.name, [alias.asname or alias.name])
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.level > 0:
                # 相对 import（同 Mod 内部），允许
                continue
            module = node.module or ""
            if not _module_is_allowed(module):
                names = [a.asname or a.name for a in node.names]
                violations.append(Violation(path, node.lineno, module, names))
    return violations


def _iter_mod_py_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for root_rel in MOD_ROOTS:
        root = repo_root / root_rel
        if not root.is_dir():
            continue
        files.extend(sorted(root.rglob("*.py")))
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="以 JSON 输出违规清单")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="仓库根（默认自动推断）",
    )
    args = parser.parse_args(argv)

    repo_root: Path = args.repo_root
    if not repo_root.is_dir():
        print(f"ERROR: repo root not a directory: {repo_root}", file=sys.stderr)
        return 2

    files = _iter_mod_py_files(repo_root)
    all_violations: list[Violation] = []
    for f in files:
        all_violations.extend(_scan_file(f))

    if args.json:
        payload = {
            "repo_root": str(repo_root).replace("\\", "/"),
            "roots_scanned": [str(p).replace("\\", "/") for p in MOD_ROOTS],
            "files_scanned": len(files),
            "allowed_prefixes": list(ALLOWED_PREFIXES),
            "forbidden_prefixes": list(FORBIDDEN_PREFIXES),
            "violation_count": len(all_violations),
            "violations": [v.to_dict() for v in all_violations],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"[mod-boundary] repo={repo_root}")
        print(f"[mod-boundary] scanned {len(files)} .py files under {len(MOD_ROOTS)} mod roots")
        print(f"[mod-boundary] allowed prefixes: {', '.join(ALLOWED_PREFIXES)}")
        if not all_violations:
            print("[mod-boundary] OK — no forbidden imports found")
        else:
            print(f"[mod-boundary] {len(all_violations)} VIOLATION(S):")
            for v in all_violations:
                rel = v.file.relative_to(repo_root) if v.file.is_absolute() else v.file
                names = ", ".join(v.names)
                print(f"  {rel}:{v.lineno}  from {v.module} import {names}")

    return 1 if all_violations else 0


if __name__ == "__main__":
    sys.exit(main())
