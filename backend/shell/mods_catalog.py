"""
Mod 列表数据源：优先读取静态 JSON（由 MODstore ``modman export-fhd-shell`` 生成），
否则回退内置常量。

说明：内置列表含 ``type=category|template`` 的目录/模板占位项（如 id=all 名称「全部」），
供历史/其它壳层用途；XCAGI 前端会按 ``type`` 过滤，不把其当作「已连接扩展 Mod」展示。

环境变量 ``FHD_SHELL_MODS_JSON`` 可覆盖默认 JSON 路径。
生成文件默认路径 ``backend/shell/fhd_shell_mods.json`` 已加入仓库根 ``.gitignore``，
需要团队共享时可删除对应 ignore 规则并将文件纳入版本控制。
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from backend.shell.mods_schemas import ModItem
from backend.shell.xcagi_mods_discover import read_manifest_dicts

logger = logging.getLogger(__name__)

_BUILTIN_RAW: tuple[dict, ...] = (
    {"id": "all", "name": "全部", "type": "category", "color": None},
    {"id": "出货明细表", "name": "出货明细表", "type": "template", "color": "green"},
    {"id": "出货记录管理", "name": "出货记录管理", "type": "template", "color": "green"},
    {"id": "产品目录表", "name": "产品目录表", "type": "template", "color": "green"},
    {"id": "原材料仓库", "name": "原材料仓库", "type": "template", "color": "green"},
    {"id": "客户管理", "name": "客户管理", "type": "template", "color": "green"},
    {"id": "汇总统计表", "name": "汇总统计表", "type": "template", "color": "green"},
    {"id": "销售报表", "name": "销售报表", "type": "template", "color": "green"},
    {"id": "价格表", "name": "价格表", "type": "template", "color": "blue", "description": "Word 价格表模板"},
    {
        "id": "价格表_excel",
        "name": "价格表(Excel)",
        "type": "template",
        "color": "green",
        "description": "Excel 价格表模板",
    },
)


def _resolved_json_path() -> Path:
    env = os.environ.get("FHD_SHELL_MODS_JSON", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).with_name("fhd_shell_mods.json")


def _load_json_rows() -> list[dict] | None:
    p = _resolved_json_path()
    if not p.is_file():
        return None
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("fhd_shell_mods.json unreadable (%s): %s", p, e)
        return None
    if isinstance(raw, dict) and isinstance(raw.get("data"), list):
        raw = raw["data"]
    if not isinstance(raw, list):
        logger.warning(
            "fhd_shell_mods.json expected a JSON array or object with key 'data', got %s",
            type(raw).__name__,
        )
        return None
    out: list[dict] = []
    for i, x in enumerate(raw):
        if isinstance(x, dict):
            out.append(x)
        else:
            logger.warning("fhd_shell_mods.json index %s skipped (not an object)", i)
    return out if out else None


def list_mod_items() -> list[ModItem]:
    """返回当前壳层展示的 mod 列表（已校验 schema）。

    顺序：先 ``XCAGI/mods/*/manifest.json`` 发现的扩展，再 fhd_shell_mods.json 或内置目录项（按 id 去重）。
    """
    discovered = read_manifest_dicts()
    seen: set[str] = {str(x.get("id", "")).strip() for x in discovered if isinstance(x, dict) and str(x.get("id", "")).strip()}
    rows = _load_json_rows()
    catalog: list[dict] = list(rows) if rows is not None else list(_BUILTIN_RAW)
    tail = [x for x in catalog if isinstance(x, dict) and str(x.get("id", "")).strip() not in seen]
    combined = [*discovered, *tail]
    try:
        return [ModItem.model_validate(x) for x in combined]
    except Exception as e:
        logger.warning("ModItem 校验失败，回退内置列表: %s", e)
        return [ModItem.model_validate(row) for row in _BUILTIN_RAW]
