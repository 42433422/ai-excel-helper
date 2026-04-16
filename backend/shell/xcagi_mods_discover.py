"""
扫描 XCAGI 仓库下的 ``mods/<mod_id>/manifest.json``，供 /api/mods 与 /api/mods/routes 使用。

前端约定：``XCAGI/mods/<id>/frontend/routes.js`` 由 Vite glob 动态加载（见 registerModRoutes.ts）。
环境变量 ``XCAGI_ROOT`` 可指向 XCAGI 目录；未设置时假定本仓库根下存在 ``XCAGI/`` 子目录。
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _effective_single_mod_id() -> str | None:
    """进程级只暴露一个扩展：优先当前请求头，其次环境变量 ``XCAGI_SINGLE_MOD_ID``。"""
    try:
        from backend.request_active_mod_ctx import get_request_active_mod_id

        ctx = get_request_active_mod_id()
        if ctx:
            return ctx
    except Exception:
        pass
    raw = os.environ.get("XCAGI_SINGLE_MOD_ID", "").strip()
    return raw or None


def _filter_manifest_rows_to_single(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    want = _effective_single_mod_id()
    if not want:
        return rows
    out = [r for r in rows if str(r.get("id", "")).strip() == want]
    if not out:
        logger.warning(
            "xcagi_mods_discover: single-mod filter id=%r matched no manifest (disk has %s)",
            want,
            [str(r.get("id")) for r in rows],
        )
    return out


def _unique_dirs(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    for p in paths:
        try:
            r = p.resolve()
        except OSError:
            continue
        k = str(r)
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out


def xcagi_root() -> Path | None:
    """
    含 ``mods/`` 子目录的 XCAGI 工程根（不是 mods 目录本身）。
    优先 ``XCAGI_ROOT``；否则依次尝试：与本包同仓库的 ``<repo>/XCAGI``、当前工作目录、向上查找。
    """
    candidates: list[Path] = []
    raw = os.environ.get("XCAGI_ROOT", "").strip()
    if raw:
        candidates.append(Path(raw).expanduser())
    here = Path(__file__).resolve()
    # backend/shell/this_file.py -> parents[2] == FHD 仓库根
    repo = here.parents[2]
    candidates.append(repo / "XCAGI")
    cwd = Path.cwd().resolve()
    candidates.append(cwd / "XCAGI")
    # 若进程 cwd 已在 XCAGI 根目录（常见：在 XCAGI 下起 uvicorn）
    if (cwd / "mods").is_dir() and (cwd / "frontend").is_dir():
        candidates.append(cwd)
    cur = cwd
    for _ in range(10):
        candidates.append(cur / "XCAGI")
        parent = cur.parent
        if parent == cur:
            break
        cur = parent

    for p in _unique_dirs(candidates):
        if not p.is_dir():
            continue
        mods = p / "mods"
        if mods.is_dir():
            logger.info("xcagi_mods_discover: using XCAGI root %s", p)
            return p
    logger.warning(
        "xcagi_mods_discover: no XCAGI root with a mods/ directory found. "
        "Set XCAGI_ROOT to your XCAGI folder, or XCAGI_MODS_DIR to .../XCAGI/mods directly."
    )
    return None


def mods_dir() -> Path | None:
    """优先 ``XCAGI_MODS_DIR``（直接指向 ``.../XCAGI/mods``），否则 ``<xcagi_root>/mods``。"""
    raw_mods = os.environ.get("XCAGI_MODS_DIR", "").strip()
    if raw_mods:
        p = Path(raw_mods).expanduser().resolve()
        if p.is_dir():
            logger.info("xcagi_mods_discover: using XCAGI_MODS_DIR %s", p)
            return p
        logger.warning("xcagi_mods_discover: XCAGI_MODS_DIR is not a directory: %s", p)
    root = xcagi_root()
    if not root:
        return None
    d = root / "mods"
    return d if d.is_dir() else None


def read_manifest_dicts() -> list[dict[str, Any]]:
    d = mods_dir()
    if not d:
        return []
    out: list[dict[str, Any]] = []
    for child in sorted(d.iterdir()):
        if not child.is_dir():
            continue
        folder_id = child.name
        if folder_id.startswith("."):
            continue
        mf = child / "manifest.json"
        if not mf.is_file():
            continue
        try:
            raw = json.loads(mf.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("skip manifest %s: %s", mf, e)
            continue
        if not isinstance(raw, dict):
            logger.warning("skip manifest %s: root must be object", mf)
            continue
        mid = str(raw.get("id") or folder_id).strip() or folder_id
        name = str(raw.get("name") or raw.get("title") or mid).strip() or mid
        item: dict[str, Any] = {
            "id": mid,
            "name": name,
            "type": str(raw.get("type") or "mod").strip() or "mod",
            "color": raw.get("color") if isinstance(raw.get("color"), str) else None,
            "description": raw.get("description") if isinstance(raw.get("description"), str) else None,
            "version": str(raw.get("version") or ""),
            "author": str(raw.get("author") or ""),
            "primary": bool(raw.get("primary")),
        }
        # 兼容：菜单在顶层 ``menu``，或在 ``frontend.menu``（与 sz-qsm-pro 等 manifest 一致）
        menu = raw.get("menu")
        if not (isinstance(menu, list) and len(menu) > 0):
            fe = raw.get("frontend")
            if isinstance(fe, dict):
                m2 = fe.get("menu")
                if isinstance(m2, list):
                    menu = m2
        if isinstance(menu, list) and menu:
            item["menu"] = menu
        wf = raw.get("workflow_employees")
        if isinstance(wf, list) and wf:
            cleaned = [x for x in wf if isinstance(x, dict)]
            if cleaned:
                item["workflow_employees"] = cleaned
        # shell_* / library_blurb：顶层 snake_case、顶层 camelCase，或 frontend.*（与 menu 的写法一致）
        fe_raw = raw.get("frontend")
        fe_dict = fe_raw if isinstance(fe_raw, dict) else None
        shell_spec = (
            ("shell_tagline", "shellTagline"),
            ("shell_menu_preset", "shellMenuPreset"),
            ("library_blurb", "libraryBlurb"),
        )
        for sk, ck in shell_spec:
            picked: str | None = None
            for src in (raw, fe_dict):
                if not isinstance(src, dict):
                    continue
                v = src.get(sk)
                if isinstance(v, str) and v.strip():
                    picked = v.strip()
                    break
                v2 = src.get(ck)
                if isinstance(v2, str) and v2.strip():
                    picked = v2.strip()
                    break
            if picked:
                item[sk] = picked
        if isinstance(raw.get("database_seed_sql"), str):
            raw_sql = str(raw["database_seed_sql"]).strip()
            if raw_sql:
                p = Path(raw_sql)
                if not p.is_absolute():
                    p = (child / raw_sql).resolve()
                item["database_seed_sql"] = str(p)
        rel_seeds: list[str] = []
        db_block = raw.get("database")
        if isinstance(db_block, dict):
            notes = db_block.get("notes_zh") or db_block.get("notes")
            if isinstance(notes, str) and notes.strip():
                item["database_notes"] = notes.strip()
        dn0 = raw.get("database_notes")
        if isinstance(dn0, str) and dn0.strip() and not item.get("database_notes"):
            item["database_notes"] = dn0.strip()
            sf = db_block.get("seed_files")
            if isinstance(sf, list):
                for x in sf:
                    if isinstance(x, str) and x.strip() and x.strip() not in rel_seeds:
                        rel_seeds.append(x.strip())
        root_sf = raw.get("database_seed_files")
        if isinstance(root_sf, list):
            for x in root_sf:
                if isinstance(x, str) and x.strip():
                    t = x.strip()
                    if t not in rel_seeds:
                        rel_seeds.append(t)
        abs_seeds: list[str] = []
        for rel in rel_seeds:
            p = Path(rel)
            if not p.is_absolute():
                p = (child / rel).resolve()
            sp = str(p)
            if sp not in abs_seeds:
                abs_seeds.append(sp)
        if abs_seeds:
            item["database_seed_files"] = abs_seeds
        out.append(item)
    return _filter_manifest_rows_to_single(out)


def route_entries() -> list[dict[str, str]]:
    """供 GET /api/mods/routes：与 registerModRoutes 的 mod_id 对齐。"""
    return [{"mod_id": row["id"], "routes_path": f"mods/{row['id']}/frontend/routes.js"} for row in read_manifest_dicts()]


def loading_status_extras() -> dict[str, Any]:
    rows = read_manifest_dicts()
    ids = [str(r["id"]) for r in rows]
    primaries = [r for r in rows if r.get("primary")]
    primary = primaries[0] if len(primaries) == 1 else None
    return {
        "discovered_mod_ids": ids,
        "mods_loaded": len(rows),
        "mods": [{"id": r["id"], "name": r["name"], "version": r.get("version", "")} for r in rows],
        "load_mismatch": False,
        "mods_disabled": False,
        "primary_mod_id": str(primary["id"]) if primary else None,
        "primary_mod_name": str(primary.get("name") or "") if primary else None,
        "primary_mod_count": len(primaries),
    }
