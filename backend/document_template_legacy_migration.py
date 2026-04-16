"""
SQLite ``templates.db`` 已弃用为运行时数据源；模板预览请使用 PostgreSQL ``document_templates``（``role=excel_export``）。

迁移脚本：``python scripts/migrate_sqlite_templates_to_pg_document_templates.py``

迁移后可通过 ``GET /api/document-templates?role=excel_export`` 与 ``GET /api/templates`` 访问同源数据（字段略有差异）。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def migrate_legacy_document_template_files() -> dict[str, Any]:
    """
    历史兼容占位：旧版会在启动时调用该函数迁移模板磁盘布局。
    当前版本已无额外动作，保留函数以避免 ImportError。
    """
    logger.info("document_template_legacy_migration: no-op migrate_legacy_document_template_files")
    return {"applied": False, "skipped": True, "reason": "no_legacy_layout_migration_needed"}


def sync_document_templates_storage_after_layout_migration(engine: Any) -> dict[str, Any]:
    """
    历史兼容占位：旧版会在布局迁移后同步 document_templates.storage_relpath。
    当前布局已统一，保留该函数仅用于兼容旧调用点。
    """
    _ = engine
    logger.info("document_template_legacy_migration: no-op storage sync")
    return {"applied": False, "skipped": True, "reason": "no_storage_sync_needed"}
