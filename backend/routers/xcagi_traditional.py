"""XCAGI 壳层：原版模式资源列表与 SSE 占位。"""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.workspace import traditional_resolve_path, traditional_workspace_root

router = APIRouter(tags=["xcagi-shell", "xcagi-traditional"])


@router.get("/traditional-mode/list")
@router.get("/traditional-mode/list/")
async def api_traditional_mode_list(path: str = "") -> dict:
    target = traditional_resolve_path(path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="path not found")
    if not target.is_dir():
        raise HTTPException(status_code=400, detail="not a directory")
    base = traditional_workspace_root()
    items: list[dict] = []
    try:
        for p in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                st = p.stat()
            except OSError:
                continue
            rel = p.relative_to(base).as_posix() if p != base else ""
            items.append(
                {
                    "name": p.name,
                    "path": rel,
                    "is_dir": p.is_dir(),
                    "isDirectory": p.is_dir(),
                    "type": "directory" if p.is_dir() else "file",
                    "size": st.st_size if p.is_file() else None,
                }
            )
    except OSError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    rel_root = target.relative_to(base).as_posix() if target != base else ""
    return {"success": True, "path": rel_root, "items": items, "entries": items}


@router.get("/traditional-mode/watch")
@router.get("/traditional-mode/watch/")
async def api_traditional_mode_watch(path: str = ""):
    t = traditional_resolve_path(path)
    if not t.exists():
        raise HTTPException(status_code=404, detail="path not found")

    async def event_gen():
        yield f"data: {json.dumps({'type': 'ready', 'path': path}, ensure_ascii=False)}\n\n"
        while True:
            await asyncio.sleep(30)
            yield f"data: {json.dumps({'type': 'heartbeat'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
