"""从修茈线上 MODstore ``/v1/mod-sync`` 拉取源码 zip 并写入本机 ``mods/``（与 Catalog 市场包安装不同）。"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from app.services.mod_zip_normalize import normalize_package_zip_path

logger = logging.getLogger(__name__)


async def fetch_modstore_library_mod_ids(base_url: str, token: str) -> list[str]:
    base = base_url.strip().rstrip("/")
    url = f"{base}/v1/mod-sync/mods"
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.get(url, headers=headers)
    if r.status_code >= 400:
        raise RuntimeError(f"列出 Mod 失败 HTTP {r.status_code}: {r.text[:500]}")
    data = r.json()
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise RuntimeError("远端返回格式异常：缺少 data 数组")
    out: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if not row.get("ok"):
            continue
        mid = str(row.get("id") or "").strip()
        if mid and "/" not in mid and "\\" not in mid:
            out.append(mid)
    return out


async def download_modstore_export_zip(base_url: str, token: str, mod_id: str) -> bytes:
    base = base_url.strip().rstrip("/")
    q = quote(mod_id, safe="")
    url = f"{base}/v1/mod-sync/export-zip/{q}"
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(timeout=300.0) as client:
        r = await client.get(url, headers=headers)
    if r.status_code >= 400:
        raise RuntimeError(f"{mod_id}: HTTP {r.status_code} {r.text[:500]}")
    return r.content


async def sync_modstore_library_to_local(
    *,
    base_url: str,
    token: str,
    mod_ids: list[str] | None,
    sync_all_ok: bool,
) -> dict[str, Any]:
    if not token:
        raise ValueError("缺少 token（修茈 Developer PAT，需含 mod:sync）")
    base = (base_url or "").strip().rstrip("/") or "https://xiu-ci.com"

    if sync_all_ok:
        id_list = await fetch_modstore_library_mod_ids(base, token)
    else:
        id_list = list(mod_ids or [])
        id_list = [x for x in id_list if x and "/" not in x and "\\" not in x]
    if not id_list:
        return {
            "success": True,
            "installed": [],
            "errors": [],
            "message": "没有可同步的 Mod（全部未通过校验或无权）",
        }

    from app.infrastructure.mods.mod_manager import get_mod_manager

    mm = get_mod_manager()
    installed: list[str] = []
    errors: list[str] = []

    for mid in id_list:
        tmp = tempfile.NamedTemporaryFile(
            prefix="xcagi-modstore-sync-", suffix=".zip", delete=False
        )
        tmp_path = tmp.name
        tmp.close()
        normalized_path = tmp_path
        try:
            body = await download_modstore_export_zip(base, token, mid)
            Path(tmp_path).write_bytes(body)
            normalized_path = normalize_package_zip_path(tmp_path)
            ok, message, metadata = mm.install_mod_package(
                normalized_path,
                verify_signature=False,
                activate=False,
            )
            if ok:
                installed.append(mid)
            else:
                errors.append(f"{mid}: {message}")
        except Exception as e:
            logger.exception("modstore sync failed for %s", mid)
            errors.append(f"{mid}: {e}")
        finally:
            for p in {tmp_path, normalized_path}:
                try:
                    if p and os.path.exists(p):
                        os.unlink(p)
                except OSError:
                    logger.warning("无法删除临时 Mod 包: %s", p)

    ok_all = not errors
    msg = f"已安装 {len(installed)} 个" + (f"，失败 {len(errors)} 个" if errors else "")
    data: dict[str, Any] = {"installed": installed, "errors": errors}
    return {"success": ok_all, "message": msg, "data": data}
