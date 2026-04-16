"""
PostgreSQL 缺省业务表时自动执行 ``scripts/pg_init_xcagi_core.sql``（幂等 ``IF NOT EXISTS``）。

由 ``get_sync_engine()`` 在首次建连后调用，消除 ``products_bulk_import`` 的 ``no_products_table``。
可用环境变量 ``FHD_AUTO_INIT_PG_SCHEMA=0`` 关闭。
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_REPO_SCRIPTS_SQL = Path(__file__).resolve().parent.parent / "scripts" / "pg_init_xcagi_core.sql"

# 脚本缺失时兜底（与 scripts/pg_init_xcagi_core.sql 保持一致）
_FALLBACK_INIT_SQL = """
CREATE TABLE IF NOT EXISTS purchase_units (
    id              SERIAL PRIMARY KEY,
    unit_name       VARCHAR(200) NOT NULL,
    contact_person  VARCHAR(200),
    contact_phone   VARCHAR(100),
    address         TEXT,
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS purchase_units_unit_name_key
    ON purchase_units (unit_name);
CREATE TABLE IF NOT EXISTS products (
    id              SERIAL PRIMARY KEY,
    model_number    VARCHAR(120),
    name            VARCHAR(500) NOT NULL,
    specification   TEXT,
    price           NUMERIC(14, 4),
    unit            VARCHAR(200) NOT NULL,
    quantity        INTEGER DEFAULT 0,
    category        VARCHAR(200),
    brand           VARCHAR(200),
    description     TEXT,
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_products_unit ON products (unit);
CREATE INDEX IF NOT EXISTS idx_products_model_number ON products (model_number);
CREATE INDEX IF NOT EXISTS idx_products_name ON products (name);
CREATE TABLE IF NOT EXISTS customers (
    id              SERIAL PRIMARY KEY,
    customer_name   VARCHAR(200) NOT NULL,
    contact_person  VARCHAR(200),
    contact_phone   VARCHAR(100),
    address         TEXT,
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_customers_customer_name ON customers (customer_name);
CREATE TABLE IF NOT EXISTS document_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            VARCHAR(64) NOT NULL UNIQUE,
    display_name    VARCHAR(255) NOT NULL,
    role            VARCHAR(32) NOT NULL,
    storage_relpath TEXT NOT NULL,
    is_default      BOOLEAN NOT NULL DEFAULT false,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    file_format     VARCHAR(16) NOT NULL DEFAULT 'docx',
    business_scope  VARCHAR(64),
    editor_payload  JSONB NOT NULL DEFAULT '{}'::jsonb,
    legacy_sqlite_id VARCHAR(36),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_document_templates_role ON document_templates (role);
CREATE INDEX IF NOT EXISTS idx_document_templates_role_active ON document_templates (role, is_active);
CREATE UNIQUE INDEX IF NOT EXISTS idx_document_templates_legacy_sqlite_id ON document_templates (legacy_sqlite_id) WHERE legacy_sqlite_id IS NOT NULL;
INSERT INTO document_templates (slug, display_name, role, storage_relpath, is_default, is_active, sort_order, file_format)
VALUES
    ('price_list_default', '默认报价表', 'price_list_docx', '424/document_templates/price_list_default.docx', true, true, 0, 'docx'),
    ('sales_delivery', '送货单', 'sales_contract_docx', '424/document_templates/送货单.xls', true, true, 0, 'xls'),
    ('sales_pzmob', '购销 / PZMOB', 'sales_contract_docx', '424/document_templates/sales_pzmob.docx', false, true, 10, 'docx'),
    ('sales_cn', '销售合同（中文文件名）', 'sales_contract_docx', '424/document_templates/sales_cn.docx', false, true, 20, 'docx')
ON CONFLICT (slug) DO NOTHING;
"""

_DOCUMENT_TEMPLATES_ONLY_SQL = """
CREATE TABLE IF NOT EXISTS document_templates (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug            VARCHAR(64) NOT NULL UNIQUE,
    display_name    VARCHAR(255) NOT NULL,
    role            VARCHAR(32) NOT NULL,
    storage_relpath TEXT NOT NULL,
    is_default      BOOLEAN NOT NULL DEFAULT false,
    is_active       BOOLEAN NOT NULL DEFAULT true,
    sort_order      INTEGER NOT NULL DEFAULT 0,
    file_format     VARCHAR(16) NOT NULL DEFAULT 'docx',
    business_scope  VARCHAR(64),
    editor_payload  JSONB NOT NULL DEFAULT '{}'::jsonb,
    legacy_sqlite_id VARCHAR(36),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_document_templates_role ON document_templates (role);
CREATE INDEX IF NOT EXISTS idx_document_templates_role_active ON document_templates (role, is_active);
CREATE UNIQUE INDEX IF NOT EXISTS idx_document_templates_legacy_sqlite_id ON document_templates (legacy_sqlite_id) WHERE legacy_sqlite_id IS NOT NULL;
INSERT INTO document_templates (slug, display_name, role, storage_relpath, is_default, is_active, sort_order, file_format)
VALUES
    ('price_list_default', '默认报价表', 'price_list_docx', '424/document_templates/price_list_default.docx', true, true, 0, 'docx'),
    ('sales_delivery', '送货单', 'sales_contract_docx', '424/document_templates/送货单.xls', true, true, 0, 'xls'),
    ('sales_pzmob', '购销 / PZMOB', 'sales_contract_docx', '424/document_templates/sales_pzmob.docx', false, true, 10, 'docx'),
    ('sales_cn', '销售合同（中文文件名）', 'sales_contract_docx', '424/document_templates/sales_cn.docx', false, true, 20, 'docx')
ON CONFLICT (slug) DO NOTHING;
"""

_DOCUMENT_TEMPLATES_ALTER_SQL = """
ALTER TABLE document_templates ADD COLUMN IF NOT EXISTS file_format VARCHAR(16) NOT NULL DEFAULT 'docx';
ALTER TABLE document_templates ADD COLUMN IF NOT EXISTS business_scope VARCHAR(64);
ALTER TABLE document_templates ADD COLUMN IF NOT EXISTS editor_payload JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE document_templates ADD COLUMN IF NOT EXISTS legacy_sqlite_id VARCHAR(36);
CREATE UNIQUE INDEX IF NOT EXISTS idx_document_templates_legacy_sqlite_id ON document_templates (legacy_sqlite_id) WHERE legacy_sqlite_id IS NOT NULL;
"""


def _auto_init_enabled() -> bool:
    v = os.environ.get("FHD_AUTO_INIT_PG_SCHEMA", "1").strip().lower()
    return v not in ("0", "false", "no", "off")


def _load_init_sql_text() -> str:
    if _REPO_SCRIPTS_SQL.is_file():
        return _REPO_SCRIPTS_SQL.read_text(encoding="utf-8")
    logger.warning("schema_auto_init: missing %s, using embedded DDL", _REPO_SCRIPTS_SQL)
    return _FALLBACK_INIT_SQL


def statements_from_init_sql(raw: str) -> list[str]:
    """去掉注释与事务包装，拆成可逐条 ``execute`` 的语句。"""
    lines: list[str] = []
    for line in raw.splitlines():
        s = line.strip()
        if not s or s.startswith("--"):
            continue
        lines.append(line)
    blob = "\n".join(lines)
    blob = re.sub(r"^\s*BEGIN\s*;\s*", "", blob, flags=re.IGNORECASE | re.MULTILINE)
    blob = re.sub(r"\s*COMMIT\s*;\s*$", "", blob, flags=re.IGNORECASE | re.MULTILINE)
    parts: list[str] = []
    for chunk in blob.split(";"):
        c = chunk.strip()
        if c:
            parts.append(c)
    return parts


def ensure_pg_core_business_tables(engine: Any) -> dict[str, Any]:
    """
    若 ``public`` 下缺少 ``products`` 或 ``purchase_units``，执行初始化 DDL。
    返回 ``{ "applied": bool, "statements_run": int, ... }``。
    """
    if not _auto_init_enabled():
        return {"applied": False, "skipped": True, "reason": "FHD_AUTO_INIT_PG_SCHEMA disabled"}

    try:
        from sqlalchemy import inspect, text
    except ImportError:
        return {"applied": False, "error": "no_sqlalchemy"}

    try:
        insp = inspect(engine)
        names = set(insp.get_table_names())
    except Exception as e:
        logger.warning("schema_auto_init: inspect failed: %s", e)
        return {"applied": False, "error": str(e)}

    if "products" in names and "purchase_units" in names:
        return {"applied": False, "skipped": True, "reason": "tables_already_present"}

    stmts = statements_from_init_sql(_load_init_sql_text())
    if not stmts:
        return {"applied": False, "error": "no_statements"}

    n_ok = 0
    try:
        with engine.begin() as conn:
            for stmt in stmts:
                conn.execute(text(stmt))
                n_ok += 1
    except Exception as e:
        logger.exception("schema_auto_init: DDL failed after %s statements: %s", n_ok, e)
        return {"applied": False, "error": str(e), "statements_run": n_ok}

    logger.info(
        "schema_auto_init: created core XCAGI tables (products, purchase_units, customers) "
        "via %d DDL statements",
        n_ok,
    )
    return {"applied": True, "statements_run": n_ok}


def ensure_document_templates_schema(engine: Any) -> dict[str, Any]:
    """
    幂等创建 ``document_templates`` 并写入默认种子行；在已有 products 的库上也会执行。
    """
    if not _auto_init_enabled():
        return {"applied": False, "skipped": True, "reason": "FHD_AUTO_INIT_PG_SCHEMA disabled"}

    try:
        from sqlalchemy import text
    except ImportError:
        return {"applied": False, "error": "no_sqlalchemy"}

    # 兼容旧库：若表已存在但缺少新增列，先补列再执行建索引/种子数据，
    # 避免在 legacy_sqlite_id 尚不存在时创建索引失败。
    pre_ext = ensure_document_templates_extended_columns(engine)
    stmts = statements_from_init_sql(_DOCUMENT_TEMPLATES_ONLY_SQL)
    if not stmts:
        return {"applied": False, "error": "no_document_template_statements"}

    n_ok = 0
    try:
        with engine.begin() as conn:
            for stmt in stmts:
                conn.execute(text(stmt))
                n_ok += 1
    except Exception as e:
        logger.exception("schema_auto_init: document_templates DDL failed after %s statements: %s", n_ok, e)
        return {"applied": False, "error": str(e), "statements_run": n_ok}

    logger.info("schema_auto_init: ensured document_templates (%d statements)", n_ok)
    ext = ensure_document_templates_extended_columns(engine)
    delivery = ensure_sales_contract_delivery_xls_default(engine)
    repair = repair_document_templates_paths_removed_shell_mod(engine)
    return {
        "applied": True,
        "statements_run": n_ok,
        "extended": ext,
        "pre_extended": pre_ext,
        "sales_delivery_default": delivery,
        "removed_shell_mod_paths_repaired": repair,
    }


def repair_document_templates_paths_removed_shell_mod(engine: Any) -> dict[str, Any]:
    """
    曾用已移除的 ``mods/fhd_default_templates/...`` 登记 ``document_templates`` 的库：把路径改回 ``424/...``，
    并去掉 ``editor_payload.source_mod``，避免删 Mod 后仍指向不存在的磁盘路径。
    """
    if not _auto_init_enabled():
        return {"applied": False, "skipped": True, "reason": "FHD_AUTO_INIT_PG_SCHEMA disabled"}

    try:
        from sqlalchemy import inspect, text
    except ImportError:
        return {"applied": False, "error": "no_sqlalchemy"}

    try:
        insp = inspect(engine)
        if "document_templates" not in insp.get_table_names():
            return {"applied": False, "skipped": True, "reason": "no_document_templates_table"}
    except Exception as e:
        return {"applied": False, "error": str(e)}

    stmt = text(
        """
        UPDATE document_templates SET
            storage_relpath = CASE slug
                WHEN 'price_list_default' THEN '424/document_templates/price_list_default.docx'
                WHEN 'sales_delivery' THEN '424/document_templates/送货单.xls'
                WHEN 'sales_pzmob' THEN '424/document_templates/sales_pzmob.docx'
                WHEN 'sales_cn' THEN '424/document_templates/sales_cn.docx'
                ELSE storage_relpath
            END,
            editor_payload = COALESCE(editor_payload, '{}'::jsonb) - 'source_mod'
        WHERE storage_relpath LIKE :pfx
        """
    )
    try:
        with engine.begin() as conn:
            r = conn.execute(stmt, {"pfx": "mods/fhd_default_templates/%"})
            n = getattr(r, "rowcount", None)
    except Exception as e:
        logger.warning("schema_auto_init: repair shell-mod template paths failed: %s", e)
        return {"applied": False, "error": str(e)}

    if n:
        logger.info("schema_auto_init: repaired %s document_templates row(s) off removed mods path", n)
    return {"applied": True, "rows_updated": int(n or 0)}


def ensure_sales_contract_delivery_xls_default(engine: Any) -> dict[str, Any]:
    """
    当仓库内存在 ``424/document_templates/送货单.xls`` 时，登记 ``sales_delivery`` 并设为
    唯一 ``is_default`` 销售合同模板，使省略 ``template_id`` 时走 Excel 分支输出 ``.xlsx``。
    """
    if not _auto_init_enabled():
        return {"applied": False, "skipped": True, "reason": "FHD_AUTO_INIT_PG_SCHEMA disabled"}

    repo = Path(__file__).resolve().parent.parent
    xls = repo / "424" / "document_templates" / "送货单.xls"
    if not xls.is_file():
        logger.info("schema_auto_init: skip sales_delivery default (missing %s)", xls)
        return {"applied": False, "skipped": True, "reason": "missing_delivery_xls"}

    try:
        from sqlalchemy import inspect, text
    except ImportError:
        return {"applied": False, "error": "no_sqlalchemy"}

    try:
        insp = inspect(engine)
        if "document_templates" not in insp.get_table_names():
            return {"applied": False, "skipped": True, "reason": "no_document_templates_table"}
    except Exception as e:
        return {"applied": False, "error": str(e)}

    slug = "sales_delivery"
    rel = "424/document_templates/送货单.xls"
    dn = "送货单"

    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    """
                    INSERT INTO document_templates (
                        slug, display_name, role, storage_relpath,
                        is_default, is_active, sort_order, file_format
                    ) VALUES (
                        :slug, :dn, 'sales_contract_docx', :rel,
                        false, true, 0, 'xls'
                    )
                    ON CONFLICT (slug) DO UPDATE SET
                        display_name = EXCLUDED.display_name,
                        storage_relpath = EXCLUDED.storage_relpath,
                        is_active = EXCLUDED.is_active,
                        file_format = EXCLUDED.file_format
                    """
                ),
                {"slug": slug, "dn": dn, "rel": rel},
            )
            conn.execute(
                text(
                    "UPDATE document_templates SET is_default = false "
                    "WHERE role = 'sales_contract_docx' AND slug <> :slug"
                ),
                {"slug": slug},
            )
            conn.execute(
                text(
                    "UPDATE document_templates SET is_default = true, sort_order = 0 "
                    "WHERE role = 'sales_contract_docx' AND slug = :slug"
                ),
                {"slug": slug},
            )
    except Exception as e:
        logger.warning("schema_auto_init: ensure_sales_contract_delivery_xls_default failed: %s", e)
        return {"applied": False, "error": str(e)}

    logger.info("schema_auto_init: sales_contract default template set to %s (%s)", slug, rel)
    return {"applied": True, "slug": slug}


def ensure_document_templates_extended_columns(engine: Any) -> dict[str, Any]:
    """为已有 ``document_templates`` 表追加 excel 预览等列（幂等）。"""
    if not _auto_init_enabled():
        return {"applied": False, "skipped": True}

    try:
        from sqlalchemy import inspect, text
    except ImportError:
        return {"applied": False, "error": "no_sqlalchemy"}

    try:
        insp = inspect(engine)
        if "document_templates" not in insp.get_table_names():
            return {"applied": False, "skipped": True, "reason": "no_document_templates_table"}
    except Exception as e:
        return {"applied": False, "error": str(e)}

    stmts = statements_from_init_sql(_DOCUMENT_TEMPLATES_ALTER_SQL)
    n_ok = 0
    try:
        with engine.begin() as conn:
            for stmt in stmts:
                conn.execute(text(stmt))
                n_ok += 1
    except Exception as e:
        logger.warning("schema_auto_init: document_templates ALTER failed after %s: %s", n_ok, e)
        return {"applied": False, "error": str(e), "statements_run": n_ok}

    if n_ok:
        logger.info("schema_auto_init: document_templates extended columns (%d statements)", n_ok)
    return {"applied": True, "statements_run": n_ok}


_MOD_ROW_SCOPE_DDL = """
ALTER TABLE products ADD COLUMN IF NOT EXISTS xcagi_mod_id VARCHAR(128);
ALTER TABLE purchase_units ADD COLUMN IF NOT EXISTS xcagi_mod_id VARCHAR(128);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS xcagi_mod_id VARCHAR(128);
CREATE INDEX IF NOT EXISTS idx_products_xcagi_mod_id ON products (xcagi_mod_id);
CREATE INDEX IF NOT EXISTS idx_purchase_units_xcagi_mod_id ON purchase_units (xcagi_mod_id);
CREATE INDEX IF NOT EXISTS idx_customers_xcagi_mod_id ON customers (xcagi_mod_id);
DROP INDEX IF EXISTS purchase_units_unit_name_key;
CREATE UNIQUE INDEX IF NOT EXISTS purchase_units_mod_unit_name_key
    ON purchase_units (COALESCE(btrim(cast(xcagi_mod_id AS text)), ''), lower(btrim(cast(unit_name AS text)))));
"""


def ensure_mod_row_scope_columns(engine: Any) -> dict[str, Any]:
    """已有库上幂等追加 xcagi_mod_id 并调整 purchase_units 唯一约束（多扩展共库）。"""
    if not _auto_init_enabled():
        return {"applied": False, "skipped": True, "reason": "FHD_AUTO_INIT_PG_SCHEMA disabled"}

    try:
        from sqlalchemy import inspect, text
    except ImportError:
        return {"applied": False, "error": "no_sqlalchemy"}

    try:
        insp = inspect(engine)
        if "products" not in insp.get_table_names() or "purchase_units" not in insp.get_table_names():
            return {"applied": False, "skipped": True, "reason": "core_tables_missing"}
    except Exception as e:
        return {"applied": False, "error": str(e)}

    stmts = statements_from_init_sql(_MOD_ROW_SCOPE_DDL)
    if not stmts:
        return {"applied": False, "error": "no_statements"}
    n_ok = 0
    try:
        with engine.begin() as conn:
            for stmt in stmts:
                conn.execute(text(stmt))
                n_ok += 1
    except Exception as e:
        logger.warning("schema_auto_init: mod row scope DDL failed after %s: %s", n_ok, e)
        return {"applied": False, "error": str(e), "statements_run": n_ok}

    if n_ok:
        logger.info("schema_auto_init: mod row scope columns / purchase_units unique (%d statements)", n_ok)
    return {"applied": True, "statements_run": n_ok}
