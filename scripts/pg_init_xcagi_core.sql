-- XCAGI / FHD 最小业务表：与 backend.products_bulk_import、backend.product_db_read 对齐。
-- 用法（示例）： psql "postgresql://xcagi:xcagi@127.0.0.1:5433/xcagi" -v ON_ERROR_STOP=1 -f scripts/pg_init_xcagi_core.sql
--
-- 注意：
--   * purchase_units 客户/购买单位列名为 unit_name（不是 name）。
--   * products.unit 存购买单位名称（与 purchase_units.unit_name 对应），与 LLM 工具里 customer_name 一致。
BEGIN;

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

-- 客户管理页 GET /api/customers/list：优先读此表（有数据时不再只用 purchase_units）
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

-- 业务 Word 模板库元数据（文件在磁盘，见 storage_relpath；slug 供前端与导出 API 传递）
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
CREATE UNIQUE INDEX IF NOT EXISTS idx_document_templates_legacy_sqlite_id
    ON document_templates (legacy_sqlite_id) WHERE legacy_sqlite_id IS NOT NULL;

-- 已有库升级：列可能已随 CREATE 存在，以下语句幂等
ALTER TABLE document_templates ADD COLUMN IF NOT EXISTS file_format VARCHAR(16) NOT NULL DEFAULT 'docx';
ALTER TABLE document_templates ADD COLUMN IF NOT EXISTS business_scope VARCHAR(64);
ALTER TABLE document_templates ADD COLUMN IF NOT EXISTS editor_payload JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE document_templates ADD COLUMN IF NOT EXISTS legacy_sqlite_id VARCHAR(36);

INSERT INTO document_templates (slug, display_name, role, storage_relpath, is_default, is_active, sort_order, file_format)
VALUES
    ('price_list_default', '默认报价表', 'price_list_docx', '424/document_templates/price_list_default.docx', true, true, 0, 'docx'),
    ('sales_delivery', '送货单', 'sales_contract_docx', '424/document_templates/送货单.xls', true, true, 0, 'xls'),
    ('sales_pzmob', '购销 / PZMOB', 'sales_contract_docx', '424/document_templates/sales_pzmob.docx', false, true, 10, 'docx'),
    ('sales_cn', '销售合同（中文文件名）', 'sales_contract_docx', '424/document_templates/sales_cn.docx', false, true, 20, 'docx')
ON CONFLICT (slug) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    role = EXCLUDED.role,
    storage_relpath = EXCLUDED.storage_relpath,
    is_default = EXCLUDED.is_default,
    is_active = EXCLUDED.is_active,
    sort_order = EXCLUDED.sort_order,
    file_format = EXCLUDED.file_format;

-- 多扩展共库：行归属（与请求头 X-XCAGI-Active-Mod-Id 配合，见 backend/shell/mod_row_scope.py）
ALTER TABLE products ADD COLUMN IF NOT EXISTS xcagi_mod_id VARCHAR(128);
ALTER TABLE purchase_units ADD COLUMN IF NOT EXISTS xcagi_mod_id VARCHAR(128);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS xcagi_mod_id VARCHAR(128);
CREATE INDEX IF NOT EXISTS idx_products_xcagi_mod_id ON products (xcagi_mod_id);
CREATE INDEX IF NOT EXISTS idx_purchase_units_xcagi_mod_id ON purchase_units (xcagi_mod_id);
CREATE INDEX IF NOT EXISTS idx_customers_xcagi_mod_id ON customers (xcagi_mod_id);
DROP INDEX IF EXISTS purchase_units_unit_name_key;
CREATE UNIQUE INDEX IF NOT EXISTS purchase_units_mod_unit_name_key
    ON purchase_units (COALESCE(btrim(cast(xcagi_mod_id AS text)), ''), lower(btrim(cast(unit_name AS text)))));

COMMIT;
