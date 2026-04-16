"""
从 MODstore library 生成 FHD XCAGI 壳层 ``GET /api/mods`` 使用的静态 JSON 列表。

输出为 JSON 数组，元素形状与 FHD ``ModItem`` 一致（id / name / type / color / description）。

manifest 可选扩展字段 ``fhd_shell``::

    "fhd_shell": {
        "type": "template",
        "color": "blue",
        "description": "壳层副标题",
        "name": "覆盖在壳列表中的显示名"
    }

未设置时：type 为 ``template``，color 为 ``green``；description 默认取 manifest 顶层 ``description``。

可选 ``database_seed_sql``（manifest 顶层或 ``fhd_shell`` 内）：相对路径相对 Mod 根解析为绝对路径，
写入壳层 JSON，供 FHD ``FHD_DB_MOD_GATE`` 通过后执行一次 PostgreSQL 种子脚本。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from modman.manifest_util import read_manifest
from modman.store import iter_mod_dirs

_CATEGORY_ALL: Dict[str, Any] = {
    "id": "all",
    "name": "全部",
    "type": "category",
    "color": None,
}


def _shell_overlay(manifest: Dict[str, Any]) -> Dict[str, Any]:
    raw = manifest.get("fhd_shell")
    return raw if isinstance(raw, dict) else {}


def _row_for_manifest(mod_dir: Path, manifest: Dict[str, Any]) -> Dict[str, Any] | None:
    mid = str(manifest.get("id") or mod_dir.name).strip()
    if not mid:
        return None
    overlay = _shell_overlay(manifest)
    name = str(overlay.get("name") or manifest.get("name") or mid).strip() or mid
    typ = str(overlay.get("type") or "template").strip() or "template"
    color = overlay.get("color", "green")
    if color is not None:
        color = str(color).strip() or "green"
    desc = overlay.get("description")
    if desc is None:
        desc = manifest.get("description")
    if desc is not None:
        desc = str(desc).strip() or None
    row: Dict[str, Any] = {"id": mid, "name": name, "type": typ, "color": color}
    if desc:
        row["description"] = desc
    raw_seed = manifest.get("database_seed_sql") or overlay.get("database_seed_sql")
    if raw_seed:
        sp = Path(str(raw_seed).strip())
        if not sp.is_absolute():
            sp = (mod_dir / sp).resolve()
        row["database_seed_sql"] = str(sp)
    return row


def build_fhd_shell_mod_rows(library: Path) -> List[Dict[str, Any]]:
    """
    扫描 library 下含 manifest.json 的 Mod 目录，生成壳层列表 dict（未校验 Pydantic）。
    若库中无任何 id 为 ``all`` 的项，则在列表首部插入「全部分类」行。
    """
    mod_rows: List[Dict[str, Any]] = []
    for d in iter_mod_dirs(library):
        data, err = read_manifest(d)
        if err or not data:
            print(f"[export-fhd-shell] 跳过（manifest 无效）: {d.name}: {err}", file=sys.stderr)
            continue
        row = _row_for_manifest(d, data)
        if row:
            mod_rows.append(row)
    mod_rows.sort(key=lambda r: str(r.get("id", "")).lower())
    if any(str(r.get("id")) == "all" for r in mod_rows):
        return mod_rows
    return [_CATEGORY_ALL, *mod_rows]


def write_fhd_shell_mods_json(library: Path, output: Path) -> int:
    rows = build_fhd_shell_mod_rows(library)
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(rows)
