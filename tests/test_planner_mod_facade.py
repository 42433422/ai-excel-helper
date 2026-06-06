# -*- coding: utf-8 -*-

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MOD_DIR = REPO / "mods" / "xcagi-planner-bridge"


def test_planner_mod_manifest_facade():
    data = json.loads((MOD_DIR / "manifest.json").read_text(encoding="utf-8"))
    assert data["id"] == "xcagi-planner-bridge"
    assert data.get("config", {}).get("planner_facade") is True


def test_planner_blueprints_exposes_chat_routes():
    text = (MOD_DIR / "backend" / "blueprints.py").read_text(encoding="utf-8")
    assert "/chat/stream" in text
    assert "/intent/test" in text
    assert "/tools/registry" in text
    assert "/tools/execute" in text
    assert "app.mod_sdk.planner_compat" in text


def test_mod_sdk_planner_compat_exports():
    from app.mod_sdk.planner_compat import PLANNER_FACADE_MOD_ID, chat, chat_batch, chat_stream

    assert PLANNER_FACADE_MOD_ID == "xcagi-planner-bridge"
    assert callable(chat) and callable(chat_batch) and callable(chat_stream)


def test_list_planner_tools_registry():
    from app.mod_sdk.planner_compat import list_planner_tools_registry

    data = list_planner_tools_registry()
    assert data.get("ok") is True
    assert isinstance(data.get("tool_names"), list)
    assert len(data["tool_names"]) >= 1
    assert "execution_path" in data
    assert "delegate" in data


def test_planner_compat_service_importable():
    from app.application.planner_compat_service import (
        execute_compat_chat,
        execute_compat_chat_batch,
    )

    assert callable(execute_compat_chat)
    assert callable(execute_compat_chat_batch)
