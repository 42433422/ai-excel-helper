-- 多扩展共库：为 products / purchase_units / customers 增加 xcagi_mod_id，并调整 purchase_units 唯一约束。
-- 与 backend/schema_auto_init.py::ensure_mod_row_scope_columns 及 scripts/pg_init_xcagi_core.sql 保持一致。
-- 用法（示例）：
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/migrate_xcagi_mod_row_scope.sql
--
-- 迁移后：请求带 X-XCAGI-Active-Mod-Id 时，业务 API 只读写 xcagi_mod_id 与当前包一致的行。
-- 旧数据 xcagi_mod_id 为 NULL 时不会出现在任何扩展的列表中；请按需执行下方「示例归属」UPDATE。

BEGIN;

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

-- ========== 示例：将历史无主数据归到指定扩展（执行前请改成真实 mod id）==========
-- UPDATE products SET xcagi_mod_id = 'sz-qsm-pro' WHERE xcagi_mod_id IS NULL;
-- UPDATE purchase_units SET xcagi_mod_id = 'sz-qsm-pro' WHERE xcagi_mod_id IS NULL;
-- UPDATE customers SET xcagi_mod_id = 'sz-qsm-pro' WHERE xcagi_mod_id IS NULL;
