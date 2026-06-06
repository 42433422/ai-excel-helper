#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
防漂移检测：禁止 XCAGI/ 下出现"和 FHD/ 同相对路径但内容不同"的代码副本。

【背景】
XCAGI 目录的设计是入口脚本目录（``XCAGI/run_fastapi.py`` 注释明确写"代码已统一至
根目录 app/"），里面 ``app/`` 是 junction 指向 ``FHD/app/``。但历史上 ``XCAGI/``
还残留 ``resources/``、``scripts/``、``alembic/`` 等老副本——一旦启动脚本里
``PYTHONPATH`` 把 XCAGI 排到 FHD 前面（``namespace package`` 先到先得），副本就
会赢主版本，造成"我改了 ``FHD/resources/config/industry_config.py`` 没生效，前端
拿到的是 4-14 老版"这类幽灵问题。

【本脚本作用】
扫描 XCAGI/ 下的代码/配置文件，与 FHD/ 同相对路径文件做内容对比：
  - 完全相同 → 忽略（无歧义）
  - 不同     → 列出，并按时间戳标 ``XCAGI_NEWER`` / ``FHD_NEWER``
  - 仅 XCAGI 有 → 忽略（多半是数据/独有目录）

任何"内容不同"都视作 violation，CI/pre-commit 跑这个脚本就能立刻拦下。

【使用】
::

    python FHD/scripts/check_no_xcagi_overrides.py
    # 退出码：0=干净；1=有漂移；2=参数/路径错误

允许通过 ``--allow`` 参数白名单某些故意保留的双副本（带"为什么"注释）。
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


# 这些子目录在 XCAGI/ 下是"独有/运行时/巨大/无关"的，扫描时直接跳过
SKIP_DIR_NAMES = {
    "__pycache__",
    "node_modules",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    ".git",
    "dist",
    "build",
    "release-bundle",
    "generated_contracts",
    "paddleocr_local_models",
    "saved_analyses",
    "logs",
    "uploads",
    "data",
    ".backups",
    "wechat_cache",
    "WechatDecrypt",
    "vectors",
    "user_memory",
    "tests",
    "test_labels",
    "labels",
    "outputs",
    "shipment_outputs",
    "temp_excel",
    "rasa",
    "miniprogram",
    "monitoring",
    "static",
    "templates",
    "experiments",
    "models",
    "yuangong",
    "WXCC",
    # 子产品 / mod 自身（应当独立维护）
    "mods",
    "MODstore",
    # XCAGI 入口里 app/ 是 junction，frontend/ 是独立子项目
    "app",
    "frontend",
}

# 这些扩展名才参与对比（其他多半是数据/二进制/媒体）
CODE_EXTENSIONS = {
    ".py",
    ".pyi",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".sh",
    ".ps1",
    ".bat",
    ".cmd",
}

# 故意保留的差异：键 = XCAGI 下的相对路径，值 = 原因
DEFAULT_ALLOWLIST: dict[str, str] = {
    # XCAGI 副本指向 ../alembic（FHD 根目录）；FHD 副本指向 ./alembic（自身）。
    # 两份都对，只是路径常量不同。
    "alembic.ini": "XCAGI 副本里 script_location 指向 ../alembic 是有意的；FHD 主副本指向 ./alembic 也是有意的。",
    # XCAGI 副本只是少了 README 注释，运行时无差异
    "k8s/kustomization.yaml": "XCAGI 副本删了两行 README 注释，行为一致。",
}


@dataclass(frozen=True)
class Drift:
    rel_path: str
    xcagi_mtime: float
    fhd_mtime: float
    newer: str  # 'XCAGI' / 'FHD' / 'TIE'

    def label(self) -> str:
        return f"{self.newer:<5}  {self.rel_path}"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_candidate_files(xcagi_root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(xcagi_root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES and not d.startswith(".")]
        for name in filenames:
            ext = os.path.splitext(name)[1].lower()
            if ext in CODE_EXTENSIONS:
                yield Path(dirpath) / name


def _resolve_repo_root(here: Path) -> Path:
    """``check_no_xcagi_overrides.py`` 位于 FHD/scripts/，向上一级即仓库根 (FHD)。"""
    return here.parent.parent.resolve()


def find_drift(repo_root: Path, allowlist: dict[str, str]) -> list[Drift]:
    xcagi_root = repo_root / "XCAGI"
    if not xcagi_root.is_dir():
        return []

    drifts: list[Drift] = []
    for x_path in _iter_candidate_files(xcagi_root):
        rel = x_path.relative_to(xcagi_root).as_posix()
        if rel in allowlist:
            continue
        f_path = repo_root / rel
        if not f_path.is_file():
            continue  # XCAGI 独有的，不算漂移
        try:
            if _sha256(x_path) == _sha256(f_path):
                continue
        except OSError:
            continue
        x_mt = x_path.stat().st_mtime
        f_mt = f_path.stat().st_mtime
        if x_mt > f_mt:
            newer = "XCAGI"
        elif f_mt > x_mt:
            newer = "FHD"
        else:
            newer = "TIE"
        drifts.append(Drift(rel_path=rel, xcagi_mtime=x_mt, fhd_mtime=f_mt, newer=newer))
    drifts.sort(key=lambda d: (d.newer, d.rel_path))
    return drifts


def _format_report(drifts: list[Drift]) -> str:
    if not drifts:
        return "[OK] XCAGI/ 与 FHD/ 之间没有漂移的代码副本。"

    lines: list[str] = []
    lines.append(f"[FAIL] 发现 {len(drifts)} 个 XCAGI/ 下与 FHD/ 同路径但内容不同的代码副本。")
    lines.append(
        "PYTHONPATH 把 XCAGI 排到 FHD 之前时，这些副本会"
        "覆盖主版本，让代码改到 FHD 看起来不生效。"
    )
    lines.append("")
    lines.append("处理建议：")
    lines.append("  - XCAGI 列：日期较新的一侧。XCAGI_NEWER 通常意味着")
    lines.append("    要把 XCAGI 那份反向同步到 FHD，再删 XCAGI 副本；")
    lines.append("    FHD_NEWER 直接删 XCAGI 副本即可。")
    lines.append("  - 如果某对差异是有意保留的，写到 DEFAULT_ALLOWLIST 里并附原因。")
    lines.append("")
    lines.append(f"{'NEWER':<5}  RELATIVE_PATH")
    lines.append("-" * 60)
    lines.extend(d.label() for d in drifts)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--repo-root", type=Path, default=None, help="FHD 仓库根；默认相对脚本位置自动解析"
    )
    parser.add_argument(
        "--allow",
        action="append",
        default=[],
        metavar="REL_PATH",
        help="额外允许差异的相对路径（追加到内置白名单）",
    )
    parser.add_argument(
        "--list-newer", choices=["XCAGI", "FHD", "TIE"], default=None, help="只列出指定方向的漂移"
    )
    args = parser.parse_args(argv)

    here = Path(__file__).resolve()
    repo_root = (args.repo_root or _resolve_repo_root(here)).resolve()
    if not (repo_root / "XCAGI").is_dir():
        print(f"[SKIP] {repo_root} 下没有 XCAGI/ 子目录，无需检查。", file=sys.stderr)
        return 0

    allowlist = dict(DEFAULT_ALLOWLIST)
    for extra in args.allow:
        allowlist[extra.replace("\\", "/")] = "CLI --allow"

    drifts = find_drift(repo_root, allowlist)
    if args.list_newer:
        drifts = [d for d in drifts if d.newer == args.list_newer]

    print(_format_report(drifts))
    return 0 if not drifts else 1


if __name__ == "__main__":
    raise SystemExit(main())
