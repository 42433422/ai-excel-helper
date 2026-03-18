from shipment_parser import ShipmentParser

# 测试订单
order_text = '七彩乐园10桶9083规格28，PE白底稀释剂180kg1桶，PE哑光白面漆5桶规格28'

# 测试解析器
parser = ShipmentParser()

# 测试编号模式
print('=== 编号模式测试 ===')
result_number = parser.parse(order_text, number_mode=True)
print('购买单位:', result_number.purchase_unit)
print('产品:')
for p in result_number.products:
    print('  ', p)

print('\n=== 自定义模式测试 ===')
result_custom = parser.parse(order_text, custom_mode=True)
print('购买单位:', result_custom.purchase_unit)
print('产品:')
for p in result_custom.products:
    print('  ', p)

print('\n=== 检查七彩乐园专属数据库 ===')
import os
unit_db_path = os.path.join('unit_databases', '七彩乐园.db')
if os.path.exists(unit_db_path):
    print(f'七彩乐园专属数据库存在: {unit_db_path}')
    # 检查数据库内容
    import sqlite3
    conn = sqlite3.connect(unit_db_path)
    cursor = conn.cursor()
    # 查看产品表
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name="products"')
    if cursor.fetchone():
        # 查看产品数量
        cursor.execute('SELECT COUNT(*) FROM products')
        count = cursor.fetchone()[0]
        print(f'产品数量: {count}')
        # 查看前5个产品
        cursor.execute('SELECT model_number, name FROM products LIMIT 5')
        products = cursor.fetchall()
        print('前5个产品:')
        for p in products:
            print(f'  型号: {p[0]}, 名称: {p[1]}')
    conn.close()
else:
    print(f'七彩乐园专属数据库不存在: {unit_db_path}')
