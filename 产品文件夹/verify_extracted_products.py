import sqlite3
import pandas as pd
import re

# 连接数据库
conn = sqlite3.connect('customer_products_final_corrected.db')

print("验证提取的产品信息...")
print("=" * 60)

# 查询所有产品信息，按客户分组
query = """
SELECT c.客户名称, p.产品型号, p.产品名称, p.规格_KG, p.单价, p.数量_件, p.数量_KG, p.金额
FROM products p
JOIN customers c ON p.客户ID = c.customer_id
LIMIT 50;
"""

products_df = pd.read_sql_query(query, conn)
print("提取的产品信息示例（前50条）：")
print(products_df)

print("\n" + "=" * 60)

# 检查是否有明显的错误，例如将日期识别为产品型号
print("检查明显的错误...")

# 统计每个客户的产品数量
customer_product_count = products_df['客户名称'].value_counts()
print(f"\n各客户产品数量统计：")
print(customer_product_count)

# 检查产品型号是否有日期格式
print(f"\n检查产品型号是否包含日期格式：")
date_pattern = r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日'
error_models = []
for index, row in products_df.iterrows():
    model = str(row['产品型号'])
    if re.match(date_pattern, model):
        error_models.append({
            '客户名称': row['客户名称'],
            '产品型号': model,
            '产品名称': row['产品名称']
        })

if error_models:
    print(f"发现 {len(error_models)} 个产品型号包含日期格式：")
    for error in error_models:
        print(f"  客户：{error['客户名称']}，错误型号：{error['产品型号']}，产品名称：{error['产品名称']}")
else:
    print("未发现产品型号包含日期格式的错误")

# 检查产品名称是否包含关键词
print(f"\n检查产品名称是否包含关键词：")
keyword_count = 0
for index, row in products_df.iterrows():
    product_name = str(row['产品名称'])
    if any(keyword in product_name for keyword in ['漆', '剂', '底', '面', '稀释', '固化']):
        keyword_count += 1

print(f"在 {len(products_df)} 个产品中，{keyword_count} 个产品名称包含关键词")

# 检查数值字段是否合理
print(f"\n检查数值字段合理性：")
# 单价合理性检查
valid_price_count = products_df[(products_df['单价'] > 0) & (products_df['单价'] < 1000)].shape[0]
print(f"单价在合理范围（0-1000）的产品数量：{valid_price_count}/{len(products_df)}")

# 规格合理性检查
valid_spec_count = products_df[(products_df['规格_KG'] > 0) & (products_df['规格_KG'] < 500)].shape[0]
print(f"规格在合理范围（0-500）的产品数量：{valid_spec_count}/{len(products_df)}")

print("\n" + "=" * 60)

# 查询每个客户的前5个产品，用于更详细的检查
print("各客户产品信息示例：")
for customer in customer_product_count.index:
    print(f"\n客户：{customer}")
    customer_products = products_df[products_df['客户名称'] == customer].head(3)
    for index, row in customer_products.iterrows():
        print(f"  型号：{row['产品型号']}，名称：{row['产品名称']}，规格：{row['规格_KG']}KG，单价：{row['单价']}元")

# 关闭数据库连接
conn.close()

print("\n" + "=" * 60)
print("验证完成！")