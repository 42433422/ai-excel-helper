# -*- coding: utf-8 -*-
"""远端 Catalog 行是否应对 XCAGI 商店展示（与 AI 市场 /api/market/catalog 对齐）。"""

from __future__ import annotations

from typing import Any

# 与 modstore_server.duty_roster.YUANGON_AREAS 编制矩阵一致（内部运维岗，非公开市场商品）
_PLANNED_DUTY_EMPLOYEE_IDS: frozenset[str] = frozenset(
    {
        "site-content-editor",
        "seo-sitemap-curator",
        "flask-entry-keeper",
        "nginx-config-engineer",
        "push-update-context-officer",
        "deploy-release-officer",
        "security-secrets-guard",
        "log-monitor-incident",
        "retention-officer",
        "dbops-engineer",
        "modstore-backend-api",
        "employee-pack-curator",
        "payment-billing-reconciler",
        "market-frontend-dev",
        "workbench-ux-stylist",
        "vibe-coding-maintainer",
        "mods-and-eskill-curator",
        "change-request-auditor",
        "daily-orchestrator",
        "intake-dispatcher",
        "task-router-officer",
        "test-qa-runner",
        "doc-knowledge-curator",
        "employee-interview-assistant",
        "employee-pack-quality-interviewer",
        "intent-analyst",
        "employee-planner",
        "artifact-generator",
        "quality-validator",
        "miniapp-builder",
        "script-binder",
        "workflow-automator",
        "pack-registrar",
        "sandbox-tester",
        "code-validator",
        "self-checker",
        "host-checker",
        "hex-quality-assessor",
    }
)


def is_internal_duty_catalog_id(pkg_id: str) -> bool:
    pid = str(pkg_id or "").strip()
    return bool(pid) and pid in _PLANNED_DUTY_EMPLOYEE_IDS


def is_planned_duty_employee_pack(pkg_id: str, artifact: str | None) -> bool:
    if is_internal_duty_catalog_id(pkg_id):
        return True
    if str(artifact or "").strip().lower() != "employee_pack":
        return False
    return is_internal_duty_catalog_id(pkg_id)


def is_public_catalog_row(row: dict[str, Any]) -> bool:
    """过滤：编制内岗、草稿、无下载地址、未上架 employee_pack。"""
    if not isinstance(row, dict):
        return False
    pid = str(row.get("id") or row.get("pkg_id") or "").strip()
    if not pid:
        return False
    ver = str(row.get("version") or "").strip()
    artifact = str(row.get("artifact") or "mod").strip().lower()

    if is_internal_duty_catalog_id(pid):
        return False

    if row.get("public_listing") is False:
        return False

    channel = str(row.get("release_channel") or "stable").strip().lower()
    if channel == "draft" or ver.startswith("draft-"):
        return False

    stored = bool(str(row.get("stored_filename") or "").strip())
    download_url = bool(str(row.get("download_url") or "").strip())
    if not stored and not download_url:
        return False

    if row.get("public_listing") is True:
        return True
    if artifact == "employee_pack":
        return False
    return True
