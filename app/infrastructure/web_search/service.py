from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

_MAX_QUERY_LEN = 400
_DEFAULT_MAX_RESULTS = 5
_DEFAULT_TIMEOUT_SEC = 12.0
_RATE_WINDOW_SEC = 60
_RATE_MAX_PER_USER = 12

_rate_buckets: dict[str, list[float]] = {}


@dataclass(frozen=True)
class WebSearchHit:
    title: str
    url: str
    snippet: str


def _rate_allow(user_key: str) -> bool:
    now = time.time()
    cutoff = now - _RATE_WINDOW_SEC
    bucket = _rate_buckets.setdefault(user_key, [])
    while bucket and bucket[0] < cutoff:
        bucket.pop(0)
    if len(bucket) >= _RATE_MAX_PER_USER:
        return False
    bucket.append(now)
    return True


def _truncate(s: str, n: int) -> str:
    s = (s or "").strip()
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


async def _tavily_search(query: str, api_key: str, max_results: int) -> list[WebSearchHit]:
    import httpx

    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_answer": False,
    }
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SEC) as client:
        r = await client.post("https://api.tavily.com/search", json=payload)
        r.raise_for_status()
        data = r.json()
    out: list[WebSearchHit] = []
    for item in data.get("results") or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        url = str(item.get("url") or "").strip()
        content = str(item.get("content") or item.get("raw_content") or "").strip()
        if not url:
            continue
        out.append(WebSearchHit(title=title or url, url=url, snippet=_truncate(content, 480)))
        if len(out) >= max_results:
            break
    return out


async def _serpapi_search(query: str, api_key: str, max_results: int) -> list[WebSearchHit]:
    import httpx

    params = {"engine": "google", "q": query, "api_key": api_key, "num": max_results}
    async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT_SEC) as client:
        r = await client.get("https://serpapi.com/search.json", params=params)
        r.raise_for_status()
        data = r.json()
    out: list[WebSearchHit] = []
    for item in data.get("organic_results") or []:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()
        link = str(item.get("link") or "").strip()
        snippet = str(item.get("snippet") or "").strip()
        if not link:
            continue
        out.append(WebSearchHit(title=title or link, url=link, snippet=_truncate(snippet, 480)))
        if len(out) >= max_results:
            break
    return out


async def kitten_web_search(
    query: str,
    *,
    user_key: str = "anonymous",
    max_results: int | None = None,
) -> dict[str, Any]:
    """
    Run web search when KITTEN_WEB_SEARCH / provider keys are configured.

    Returns:
        {"success": bool, "hits": [...], "provider": str|None, "message": str?}
    """
    q = (query or "").strip()
    if len(q) > _MAX_QUERY_LEN:
        q = q[:_MAX_QUERY_LEN]

    mr = (
        max_results
        if max_results is not None
        else int(os.environ.get("WEB_SEARCH_MAX_RESULTS", str(_DEFAULT_MAX_RESULTS)))
    )
    mr = max(1, min(mr, 10))

    provider = (os.environ.get("WEB_SEARCH_PROVIDER") or "").strip().lower()
    if provider in ("", "none", "off", "0", "false"):
        return {
            "success": False,
            "hits": [],
            "provider": None,
            "message": "联网搜索未配置（WEB_SEARCH_PROVIDER）",
        }

    if not q:
        return {"success": False, "hits": [], "provider": provider, "message": "查询为空"}

    if not _rate_allow(user_key):
        return {
            "success": False,
            "hits": [],
            "provider": provider,
            "message": "搜索过于频繁，请稍后再试",
        }

    tavily_key = (os.environ.get("TAVILY_API_KEY") or "").strip()
    serp_key = (os.environ.get("SERPAPI_API_KEY") or "").strip()

    try:
        if provider == "tavily":
            if not tavily_key:
                return {
                    "success": False,
                    "hits": [],
                    "provider": "tavily",
                    "message": "缺少 TAVILY_API_KEY",
                }
            hits = await _tavily_search(q, tavily_key, mr)
        elif provider in ("serpapi", "serp"):
            if not serp_key:
                return {
                    "success": False,
                    "hits": [],
                    "provider": "serpapi",
                    "message": "缺少 SERPAPI_API_KEY",
                }
            hits = await _serpapi_search(q, serp_key, mr)
        elif provider == "auto":
            if tavily_key:
                hits = await _tavily_search(q, tavily_key, mr)
                provider = "tavily"
            elif serp_key:
                hits = await _serpapi_search(q, serp_key, mr)
                provider = "serpapi"
            else:
                return {
                    "success": False,
                    "hits": [],
                    "provider": None,
                    "message": "auto 模式需配置 TAVILY_API_KEY 或 SERPAPI_API_KEY",
                }
        else:
            return {
                "success": False,
                "hits": [],
                "provider": provider,
                "message": f"未知 WEB_SEARCH_PROVIDER={provider}，支持 tavily | serpapi | auto",
            }

        return {
            "success": True,
            "hits": [{"title": h.title, "url": h.url, "snippet": h.snippet} for h in hits],
            "provider": provider,
            "query": q,
        }
    except Exception as e:
        logger.warning("web search failed: %s", e)
        return {"success": False, "hits": [], "provider": provider, "message": str(e)}
