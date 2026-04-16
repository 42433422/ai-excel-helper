import os
os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg://xcagi:xcagi@127.0.0.1:5432/xcagi')
from sqlalchemy import create_engine, text
engine = create_engine('postgresql+psycopg://xcagi:xcagi@127.0.0.1:5432/xcagi')

with engine.begin() as conn:
    print('=== 1. 禁用现有的 Word 模板 ===')
    result = conn.execute(text("""
        UPDATE document_templates
        SET is_default = false
        WHERE role = 'sales_contract_docx'
    """))
    print(f'更新了 {result.rowcount} 行')

    print()
    print('=== 2. 插入或更新 Excel 模板 (sales_delivery) ===')
    result = conn.execute(text("""
        INSERT INTO document_templates (slug, display_name, role, storage_relpath, is_default, is_active, sort_order)
        VALUES ('sales_delivery', '送货单', 'sales_contract_docx', '424/document_templates/送货单.xls', true, true, 0)
        ON CONFLICT (slug) DO UPDATE SET
            display_name = EXCLUDED.display_name,
            storage_relpath = EXCLUDED.storage_relpath,
            is_default = EXCLUDED.is_default,
            is_active = EXCLUDED.is_active,
            sort_order = EXCLUDED.sort_order
    """))
    print('插入/更新成功')

    print()
    print('=== 3. 确认最终结果 ===')
    result = conn.execute(text("""
        SELECT slug, display_name, is_default, is_active, storage_relpath
        FROM document_templates
        WHERE role = 'sales_contract_docx'
        ORDER BY sort_order, display_name
    """))
    for row in result:
        print(row)

print()
print('=== 完成！重启后端服务后生效 ===')