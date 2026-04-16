"""
代码编辑器 / Agent 编排占位 API。

实现完整 analyze/edit/diff/apply 前，先暴露契约与探测端点，便于 OpenAPI 与智脑页联调。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body

router = APIRouter(prefix="/api/code-editor", tags=["code-editor"])


@router.get("/status")
def code_editor_status() -> dict[str, Any]:
    """健康与能力占位说明。"""
    return {
        "success": True,
        "phase": "placeholder",
        "version": 0,
        "capabilities": ["status"],
        "message": "code-editor 路由已注册；分析/编辑/应用仍为规划项。",
    }


@router.post("/analyze")
def code_editor_analyze(body: dict = Body(default_factory=dict)) -> dict[str, Any]:
    """占位：未来将合并 runtime_context 与 Planner 工具。"""
    _ = body
    return {
        "success": False,
        "placeholder": True,
        "message": "尚未实现：将接入工作区根目录校验与只读分析 Skill。",
    }


@router.post("/edit")
def code_editor_edit(body: dict = Body(default_factory=dict)) -> dict[str, Any]:
    _ = body
    return {
        "success": False,
        "placeholder": True,
        "message": "尚未实现：将返回结构化编辑建议或 patch。",
    }


@router.get("/diff/{diff_id}")
def code_editor_diff(diff_id: str) -> dict[str, Any]:
    _ = diff_id
    return {
        "success": False,
        "placeholder": True,
        "message": "尚未实现：将返回 unified diff 或结构化 diff。",
    }


@router.post("/apply/{apply_id}")
def code_editor_apply(apply_id: str, body: dict = Body(default_factory=dict)) -> dict[str, Any]:
    _ = (apply_id, body)
    return {
        "success": False,
        "placeholder": True,
        "message": "尚未实现：将在校验 P2 与工作区后应用补丁。",
    }
