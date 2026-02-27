import sqlite3

# 连接数据库
conn = sqlite3.connect('customer_products_final_corrected.db')
cursor = conn.cursor()

# 查看数据库中的所有表
print("数据库中的表：")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
for table in tables:
    print(table[0])

# 查看每个表的结构
print("\n" + "="*60 + "\n")
for table in tables:
    table_name = table[0]
    print(f"表 {table_name} 的结构：")
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    for column in columns:
        print(f"  {column[1]} ({column[2]})")
    print()

# 关闭数据库连接
conn.close()