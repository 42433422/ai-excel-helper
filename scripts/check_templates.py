import os
os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg://xcagi:xcagi@127.0.0.1:5432/xcagi')
from sqlalchemy import create_engine, text
engine = create_engine('postgresql+psycopg://xcagi:xcagi@127.0.0.1:5432/xcagi')
with engine.connect() as conn:
    print('=== document_templates 表结构 ===')
    result = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'document_templates'"))
    for row in result:
        print(row)

    print()
    print('=== 销售合同模板记录 ===')
    result = conn.execute(text("SELECT slug, display_name, is_default, storage_relpath FROM document_templates WHERE role = 'sales_contract_docx'"))
    for row in result:
        print(row)