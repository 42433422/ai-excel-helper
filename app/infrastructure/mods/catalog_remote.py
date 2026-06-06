"""从公网 Catalog 拉取包索引，与本地 mod_index 合并。"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


def catalog_base_url() -> str:
    return (os.environ.get("XCAGI_MOD_CATALOG_URL") or "").strip().rstrip("/")


def fetch_remote_package_list(timeout_s: float = 12.0) -> list[dict[str, Any]]:
    base = catalog_base_url()
    if not base:
        return []
    url = f"{base}/v1/index.json"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
        data = json.loads(raw)
        pkgs = data.get("packages")
        if isinstance(pkgs, list):
            return [x for x in pkgs if isinstance(x, dict)]
    except urllib.error.URLError as e:
        logger.warning("Remote catalog fetch failed: %s", e)
    except json.JSONDecodeError as e:
        logger.warning("Remote catalog JSON invalid: %s", e)
    except Exception as e:
        logger.warning("Remote catalog error: %s", e)
    return []


def merge_catalog_rows(
    local_rows: list[dict[str, Any]],
    remote_rows: list[dict[str, Any]],
    *,
    prefer_remote_fields: bool = True,
) -> list[dict[str, Any]]:
    """按 id+version 去重；本地优先保留 package_file，远程补 artifact/commerce/download_url。"""
    key = lambda r: (str(r.get("id") or ""), str(r.get("version") or ""))
    merged: dict[tuple, dict[str, Any]] = {}
    for r in local_rows:
        if not isinstance(r, dict):
            continue
        merged[key(r)] = dict(r)
    for r in remote_rows:
        if not isinstance(r, dict):
            continue
        k = key(r)
        if k not in merged:
            row = dict(r)
            row.setdefault("package_file", "")
            row["source"] = "remote"
            merged[k] = row
        elif prefer_remote_fields:
            base = merged[k]
            for fld in ("download_url", "sha256", "artifact", "commerce", "license", "tags"):
                if r.get(fld) is not None:
                    base[fld] = r[fld]
            base["source"] = "remote+local"
    return list(merged.values())
