from shipment_parser import ShipmentParser
import os

# 测试订单
order_text = '七彩乐园10桶9083规格28，PE白底稀释剂180kg1桶，PE哑光白面漆5桶规格28'

# 测试解析器
parser = ShipmentParser()

# 手动测试数据库选择逻辑
print('=== 数据库选择测试 ===')
unit_name = '七彩乐园'
unit_db_name = f"{unit_name}.db"
unit_db_path = os.path.join(parser.unit_database_dir, unit_db_name)
print(f'单位数据库目录: {parser.unit_database_dir}')
print(f'七彩乐园数据库路径: {unit_db_path}')
print(f'文件存在: {os.path.exists(unit_db_path)}')

print('\n=== 测试关键词提取 ===')
# 测试分割产品
product_items = parser._split_products(order_text, unit_name)
print(f'分割后的产品: {product_items}')

# 测试单个产品解析
for i, item in enumerate(product_items):
    print(f'\n--- 产品 {i+1}: {item} ---')
    # 清理文本
    import re
    search_text = re.sub(r'\d+\s*(?:桶|kg|千克|公斤)', '', item)
    print(f'清理后: {search_text}')
    # 提取关键词
    keywords = parser._extract_product_keywords(search_text)
    print(f'关键词: {keywords}')

print('\n=== 测试数据库查询 ===')
if os.path.exists(unit_db_path):
    import sqlite3
    conn = sqlite3.connect(unit_db_path)
    cursor = conn.cursor()
    # 搜索9083
    cursor.execute('SELECT model_number, name FROM products WHERE model_number LIKE ? OR name LIKE ?', ['%9083%', '%9083%'])
    results = cursor.fetchall()
    print('搜索9083的结果:')
    for r in results:
        print(f'  型号: {r[0]}, 名称: {r[1]}')
    # 搜索PE白底稀释剂
    cursor.execute('SELECT model_number, name FROM products WHERE name LIKE ?', ['%PE%白底%稀释剂%'])
    results = cursor.fetchall()
    print('搜索PE白底稀释剂的结果:')
    for r in results:
        print(f'  型号: {r[0]}, 名称: {r[1]}')
    conn.close()
