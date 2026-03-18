import sqlite3

# 连接到数据库
conn = sqlite3.connect('customer_products_final_corrected.db')
cursor = conn.cursor()

# 查询所有客户信息
cursor.execute('SELECT 客户名称, 联系人 FROM customers')
customers = cursor.fetchall()

print("客户信息验证:")
print("客户名称 | 联系人")
print("-" * 30)

for customer in customers:
    print(f"{customer[0]} | {customer[1]}")

conn.close()