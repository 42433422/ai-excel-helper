"""Client for the remote MODstore public catalog."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, AsyncIterator
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

DEFAULT_CATALOG_BASE_URL = "https://xiu-ci.com/v1"
DEFAULT_MARKET_CATALOG_URL = "https://xiu-ci.com/api/market/catalog"


def catalog_base_url() -> str:
    """Return the configured public catalog base URL without a trailing slash."""
    raw = os.environ.get("XCAGI_CATALOG_BASE_URL", DEFAULT_CATALOG_BASE_URL)
    base = (raw or DEFAULT_CATALOG_BASE_URL).strip().rstrip("/")
    return base or DEFAULT_CATALOG_BASE_URL


def market_catalog_list_url() -> str:
    """与 SUNBIRD 市场「全部商品」同一列表 API。"""
    explicit = (os.environ.get("XCAGI_MARKET_CATALOG_URL") or "").strip().rstrip("/")
    if explicit:
        return explicit
    parsed = urlparse(catalog_base_url())
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}/api/market/catalog"
    return DEFAULT_MARKET_CATALOG_URL


def _use_market_catalog() -> bool:
    raw = (os.environ.get("XCAGI_CATALOG_USE_MARKET") or "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _catalog_headers() -> dict[str, str]:
    token = (os.environ.get("XCAGI_CATALOG_TOKEN") or "").strip()
    return {"Authorization": f"Bearer {token}"} if token else {}


def _catalog_url(path: str) -> str:
    parsed = urlparse(path)
    if parsed.scheme in {"http", "https"}:
        return path
    clean = path if path.startswith("/") else f"/{path}"
    if clean.startswith("/v1/"):
        clean = clean[3:]
    return f"{catalog_base_url()}{clean}"


async def _http_get_json(url: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, headers=_catalog_headers())
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"远端 Catalog 不可达：{exc}") from exc
    if resp.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=f"远端 Catalog 返回 {resp.status_code}: {resp.text[:300]}",
        )
    try:
        data = resp.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="远端 Catalog 返回的不是 JSON") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="远端 Catalog JSON 根节点不是对象")
    return data


async def catalog_get_json(path: str) -> dict[str, Any]:
    """GET a JSON document from the remote /v1 catalog."""
    return await _http_get_json(_catalog_url(path))


def _market_item_to_package_row(item: dict[str, Any]) -> dict[str, Any] | None:
    pid = str(item.get("pkg_id") or "").strip()
    if not pid:
        return None
    ver = str(item.get("version") or "1.0.0").strip() or "1.0.0"
    price = float(item.get("price") or 0)
    return {
        "id": pid,
        "pkg_id": pid,
        "name": item.get("name") or pid,
        "version": ver,
        "description": str(item.get("description") or "").strip(),
        "artifact": item.get("artifact") or "employee_pack",
        "download_url": f"/v1/packages/{pid}/{ver}/download",
        "public_listing": True,
        "commerce": {
            "mode": "free" if price <= 0 else "paid",
            "price": price,
            "collection": item.get("collection"),
        },
        "license": item.get("license"),
    }


async def _fetch_market_catalog_rows() -> list[dict[str, Any]]:
    """拉取与市场页一致的已上架商品（分页合并）。"""
    base = market_catalog_list_url()
    out: list[dict[str, Any]] = []
    offset = 0
    limit = 200
    total = None
    while True:
        sep = "&" if "?" in base else "?"
        url = f"{base}{sep}limit={limit}&offset={offset}"
        data = await _http_get_json(url)
        items = data.get("items")
        if not isinstance(items, list):
            raise HTTPException(status_code=502, detail="市场 Catalog items 字段不是数组")
        if total is None:
            try:
                total = int(data.get("total") or 0)
            except (TypeError, ValueError):
                total = len(items)
        for raw in items:
            if not isinstance(raw, dict):
                continue
            row = _market_item_to_package_row(raw)
            if row:
                out.append(row)
        offset += len(items)
        if not items or offset >= (total or 0):
            break
        if offset > 2000:
            logger.warning("market catalog pagination stopped at offset=%s", offset)
            break
    return out


async def catalog_download_to(path: str, dest: Path) -> None:
    """Stream a catalog artifact into ``dest``."""
    url = _catalog_url(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("GET", url, headers=_catalog_headers()) as resp:
                if resp.status_code >= 400:
                    text = await resp.aread()
                    raise HTTPException(
                        status_code=502,
                        detail=f"远端 Mod 包下载失败 {resp.status_code}: {text[:300].decode('utf-8', 'ignore')}",
                    )
                with dest.open("wb") as fh:
                    async for chunk in resp.aiter_bytes():
                        if chunk:
                            fh.write(chunk)
    except HTTPException:
        raise
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"远端 Mod 包下载不可达：{exc}") from exc


async def iter_catalog_packages() -> AsyncIterator[dict[str, Any]]:
    """Yield 可安装包：默认与 SUNBIRD 市场同源（/api/market/catalog），失败时回退过滤后的 index.json。"""
    from app.services.catalog_visibility import is_public_catalog_row

    if _use_market_catalog():
        try:
            rows = await _fetch_market_catalog_rows()
            if rows:
                for row in rows:
                    if is_public_catalog_row(row):
                        yield row
                return
        except HTTPException:
            logger.warning(
                "market catalog unavailable, falling back to /v1/index.json", exc_info=True
            )
        except Exception as exc:
            logger.warning("market catalog failed: %s; fallback to index.json", exc)

    data = await catalog_get_json("/index.json")
    packages = data.get("packages") or []
    if not isinstance(packages, list):
        raise HTTPException(status_code=502, detail="远端 Mod Catalog packages 字段不是数组")
    for row in packages:
        if isinstance(row, dict) and is_public_catalog_row(row):
            yield row
