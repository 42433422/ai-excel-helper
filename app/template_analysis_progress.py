"""进程内模板分析任务进度（与归档 ``templates.analysis_progress`` 对齐）。"""

from __future__ import annotations

import threading
from typing import Any

_lock = threading.Lock()
_analysis_progress: dict[str, dict[str, Any]] = {}


def get_template_analysis_progress(task_id: str) -> dict[str, Any]:
    with _lock:
        p = _analysis_progress.get(task_id, {})
    return {
        "success": True,
        "task_id": task_id,
        "progress": p.get("percent", 0),
        "step": p.get("step", 1),
        "message": p.get("message", "准备中..."),
        "completed": p.get("completed", False),
    }


def set_template_analysis_progress(task_id: str, **fields: Any) -> None:
    with _lock:
        cur = _analysis_progress.setdefault(task_id, {})
        cur.update(fields)


def clear_template_analysis_progress(task_id: str) -> None:
    with _lock:
        _analysis_progress.pop(task_id, None)
