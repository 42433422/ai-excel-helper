import sqlite3

# 连接到数据库
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# 检查orders表是否存在
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders';")
orders_table_exists = cursor.fetchone() is not None
print('Orders table exists:', orders_table_exists)

# 如果orders表存在，查看其结构
if orders_table_exists:
    print('\nOrders table schema:')
    cursor.execute('PRAGMA table_info(orders);')
    for row in cursor.fetchall():
        print(row)

# 检查shipment_records表是否存在
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='shipment_records';")
shipment_table_exists = cursor.fetchone() is not None
print('\nShipment records table exists:', shipment_table_exists)

# 如果shipment_records表存在，查看其结构
if shipment_table_exists:
    print('\nShipment records table schema:')
    cursor.execute('PRAGMA table_info(shipment_records);')
    for row in cursor.fetchall():
        print(row)

# 关闭连接
cursor.close()
conn.close()