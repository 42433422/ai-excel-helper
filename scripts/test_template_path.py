import os
import sys
sys.path.insert(0, r'E:\FHD')
os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg://xcagi:xcagi@127.0.0.1:5432/xcagi')
from backend.document_template_service import resolve_template_path_with_meta, ROLE_SALES_CONTRACT

print('=== 测试 resolve_template_path_with_meta ===')
result = resolve_template_path_with_meta(role=ROLE_SALES_CONTRACT, slug=None)
print(f'无slug参数时: {result}')
if result[0]:
    print(f'  路径存在: {result[0].is_file()}')

result2 = resolve_template_path_with_meta(role=ROLE_SALES_CONTRACT, slug='sales_delivery')
print(f'sales_delivery: {result2}')
if result2[0]:
    print(f'  路径存在: {result2[0].is_file()}')