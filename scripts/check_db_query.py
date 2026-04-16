import os
import sys
sys.path.insert(0, r'E:\FHD')
os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg://xcagi:xcagi@127.0.0.1:5432/xcagi')

from sqlalchemy import create_engine, text
engine = create_engine('postgresql+psycopg://xcagi:xcagi@127.0.0.1:5432/xcagi')

with engine.begin() as conn:
    print('=== 查询默认模板 ===')
    result = conn.execute(text("""
        SELECT slug, storage_relpath, is_default, is_active
        FROM document_templates
        WHERE role = 'sales_contract_docx'
        AND is_default = true
        AND is_active = true
    """))
    row = result.mappings().first()
    if row:
        print(f'默认模板：{row["slug"]} -> {row["storage_relpath"]}')
    else:
        print('没有默认模板')

    print()
    print('=== 查询所有激活模板（Excel 优先）===')
    result = conn.execute(text("""
        SELECT slug, storage_relpath, is_default, is_active,
               (CASE WHEN storage_relpath ~* '\.(xls|xlsx|xlsm)$' THEN 0 ELSE 1 END) as is_word
        FROM document_templates
        WHERE role = 'sales_contract_docx'
        AND is_active = true
        ORDER BY (CASE WHEN storage_relpath ~* '\.(xls|xlsx|xlsm)$' THEN 0 ELSE 1 END), sort_order, display_name
    """))
    for row in result:
        print(f'{row["slug"]:20} {row["storage_relpath"]:40} is_default={row["is_default"]} is_word={row["is_word"]}')