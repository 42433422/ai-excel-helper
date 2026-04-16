"""
业务数据与 **XCAGI 磁盘扩展 Mod**（``mods/<id>/manifest.json``）绑定（可选开关）。

- 请求携带 ``X-Client-Mods-Off`` / ``X-XCAGI-Client-Mods-Off``（值为 ``1`` / ``true`` / ``yes`` / ``on``，与前端「原版模式」一致）时：
  **始终**不暴露业务读数据（与是否设置环境变量、磁盘上是否有扩展 Mod 无关）。
- ``FHD_BUSINESS_DATA_REQUIRES_EXTENSION_MOD=1``（或 ``true`` / ``on``）：还须至少发现一个**扩展型** manifest，
  否则产品 / 单位 / 客户列表与 ``document_templates`` 列表等对 API 返回**空**（库内数据不删，仅不暴露）。
- 未设置或非真值：除「原版模式」请求头外，始终按库内真实数据返回。

「扩展型」与前端侧栏一致：``id`` 非空且非 ``all``；``type`` 不为 ``category`` / ``template`` / ``shell_seed``。

XCAGI 自带启动脚本 ``xcagi-backend-8000.cmd`` 会默认设置 ``=1``；纯命令行起 uvicorn 时需自行 export。
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


def business_data_requires_extension_mod() -> bool:
    """是否启用「无扩展 Mod 则业务读为空」。"""
    raw = os.environ.get("FHD_BUSINESS_DATA_REQUIRES_EXTENSION_MOD", "").strip()
    return raw.lower() in ("1", "true", "yes", "on")


def is_extension_mod_manifest_row(row: dict[str, Any]) -> bool:
    mid = str(row.get("id") or "").strip()
    if not mid or mid.lower() == "all":
        return False
    t = str(row.get("type") or "mod").strip().lower()
    if t in ("category", "template", "shell_seed"):
        return False
    return True


def extension_mod_manifest_rows() -> list[dict[str, Any]]:
    try:
        from backend.shell.xcagi_mods_discover import read_manifest_dicts
    except Exception as e:
        logger.warning("mod_business_scope: read_manifest_dicts failed: %s", e)
        return []
    return [r for r in read_manifest_dicts() if isinstance(r, dict) and is_extension_mod_manifest_row(r)]


def business_data_exposed() -> bool:
    """为 True 时允许返回 products / purchase_units / customers / 模板列表等业务读数据。"""
    try:
        from backend.request_client_mods_ctx import get_request_client_mods_ui_off

        if get_request_client_mods_ui_off():
            return False
    except Exception:
        pass
    if not business_data_requires_extension_mod():
        return True
    return len(extension_mod_manifest_rows()) > 0


def business_data_hidden_reason() -> str | None:
    if business_data_exposed():
        return None
    try:
        from backend.request_client_mods_ctx import get_request_client_mods_ui_off

        if get_request_client_mods_ui_off():
            return (
                "当前为「原版模式」（请求带 X-Client-Mods-Off / X-XCAGI-Client-Mods-Off），"
                "产品/客户/单位与模板列表等对 API 暂不返回数据。"
            )
    except Exception:
        pass
    return (
        "已启用 FHD_BUSINESS_DATA_REQUIRES_EXTENSION_MOD：当前在 XCAGI/mods 下未发现可用扩展 manifest，"
        "产品/客户/单位与模板列表已对 API 隐藏。请部署扩展 Mod 或取消该环境变量。"
    )
