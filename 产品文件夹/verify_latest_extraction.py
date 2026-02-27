import sqlite3
import pandas as pd
import re
import openpyxl

# 连接数据库
conn = sqlite3.connect('customer_products_final_corrected.db')

print("验证最新提取的产品信息...")
print("=" * 60)

# 查询所有客户的产品数量
customer_count_query = """
SELECT c.客户名称, COUNT(*) as product_count
FROM products p
JOIN customers c ON p.客户ID = c.customer_id
GROUP BY c.客户名称
ORDER BY product_count DESC;
"""

customer_count = pd.read_sql_query(customer_count_query, conn)
print("各客户产品数量统计：")
print(customer_count)

print("\n" + "=" * 60)

# 检查几个代表性客户的产品信息
print("检查代表性客户的产品信息：")

# 选择几个代表性客户
representative_customers = ['七彩乐园', '尹玉华1', '志泓', '新旺博旺']

for customer in representative_customers:
    query = f"""
    SELECT p.产品型号, p.产品名称, p.规格_KG, p.单价, p.数量_件, p.数量_KG, p.金额
    FROM products p
    JOIN customers c ON p.客户ID = c.customer_id
    WHERE c.客户名称 = '{customer}'
    LIMIT 10;
    """
    
    products_df = pd.read_sql_query(query, conn)
    print(f"\n客户：{customer}")
    print(products_df)
    
    # 检查是否有明显错误
    has_errors = False
    for index, row in products_df.iterrows():
        # 检查产品型号是否包含日期或其他错误格式
        model = str(row['产品型号'])
        if re.match(r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日', model):
            print(f"  ❌ 错误：产品型号包含日期格式：{model}")
            has_errors = True
        
        # 检查数值字段是否合理
        if row['单价'] > 1000 or row['单价'] < 0:
            print(f"  ❌ 错误：单价不合理：{row['单价']}")
            has_errors = True
        if row['规格_KG'] > 500 or row['规格_KG'] < 0:
            print(f"  ❌ 错误：规格不合理：{row['规格_KG']}")
            has_errors = True
    
    if not has_errors:
        print("  ✔️ 未发现明显错误")

print("\n" + "=" * 60)

# 详细检查一个文件的原始数据和提取结果
print("详细检查原始Excel文件与提取结果的对应关系...")

# 选择七彩乐园.xlsx进行详细检查
file_path = 'e:\\女娲1号\\发货单\\七彩乐园.xlsx'
print(f"检查文件：{file_path}")

# 使用openpyxl加载工作簿
wb = openpyxl.load_workbook(file_path)
ws = wb['25出货']  # 使用出货工作表

# 查看原始数据的前15行（包括标题）
print("\n原始Excel数据（前15行）：")
for row_idx in range(1, 16):
    row = ws[row_idx]
    row_values = []
    for cell in row:
        row_values.append(cell.value)
    print(f"行 {row_idx}: {row_values[:12]}")  # 只显示前12列

# 对比提取结果
print("\n提取结果对比：")
query = """
SELECT p.产品型号, p.产品名称, p.规格_KG, p.单价, p.数量_件, p.数量_KG, p.金额
FROM products p
JOIN customers c ON p.客户ID = c.customer_id
WHERE c.客户名称 = '七彩乐园'
ORDER BY p.product_id
LIMIT 10;
"""

extracted_products = pd.read_sql_query(query, conn)
print(extracted_products)

# 关闭数据库连接和工作簿
conn.close()
wb.close()

print("\n" + "=" * 60)
print("验证完成！")