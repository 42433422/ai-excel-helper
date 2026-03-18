import sqlite3
import pandas as pd

# 连接数据库
conn = sqlite3.connect('customer_products_final_corrected.db')

# 查询所有客户的产品信息，按客户名称分组
query = """
SELECT c.客户名称, COUNT(*) as product_count,
       COUNT(DISTINCT p.产品名称) as distinct_products
FROM products p
JOIN customers c ON p.客户ID = c.customer_id
GROUP BY c.客户名称
ORDER BY product_count DESC
"""

# 执行查询
customer_summary = pd.read_sql_query(query, conn)
print("客户产品数量统计：")
print(customer_summary)
print("\n" + "="*60 + "\n")

# 查询蕊芯的产品信息（正确示例）
query_ruixin = """
SELECT c.客户名称, p.产品名称, p.产品型号, p.规格_KG, p.单价
FROM products p
JOIN customers c ON p.客户ID = c.customer_id
WHERE c.客户名称 = '蕊芯'
LIMIT 10
"""

# 查询其他几个客户的产品信息（错误示例）
query_others = """
SELECT c.客户名称, p.产品名称, p.产品型号, p.规格_KG, p.单价
FROM products p
JOIN customers c ON p.客户ID = c.customer_id
WHERE c.客户名称 != '蕊芯'
LIMIT 20
"""

print("蕊芯的产品信息（正确示例）：")
ruixin_products = pd.read_sql_query(query_ruixin, conn)
print(ruixin_products)
print("\n" + "="*60 + "\n")

print("其他客户的产品信息（错误示例）：")
other_products = pd.read_sql_query(query_others, conn)
print(other_products)

# 关闭数据库连接
conn.close()