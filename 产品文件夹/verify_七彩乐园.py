import sqlite3
import pandas as pd
import re

# 连接数据库
conn = sqlite3.connect('customer_products_final_corrected.db')

print("验证七彩乐园提取的产品信息...")
print("=" * 60)

# 查询七彩乐园的所有产品信息
query = """
SELECT p.产品型号, p.产品名称, p.规格_KG, p.单价, p.数量_件, p.数量_KG, p.金额, p.单号
FROM products p
JOIN customers c ON p.客户ID = c.customer_id
WHERE c.客户名称 = '七彩乐园'
LIMIT 20;
"""

products_df = pd.read_sql_query(query, conn)
print("七彩乐园提取的产品信息示例（前20条）：")
print(products_df)

print("\n" + "=" * 60)

# 检查是否有明显的错误，例如将日期识别为产品型号
print("检查明显的错误...")

# 查询所有七彩乐园产品，以便更全面地检查
all_products_query = """
SELECT p.产品型号, p.产品名称
FROM products p
JOIN customers c ON p.客户ID = c.customer_id
WHERE c.客户名称 = '七彩乐园';
"""

all_products_df = pd.read_sql_query(all_products_query, conn)
print(f"共提取了 {len(all_products_df)} 个产品")

# 检查产品型号是否有日期格式
date_pattern = r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日'
error_models = []
for index, row in all_products_df.iterrows():
    model = str(row['产品型号'])
    if re.match(date_pattern, model):
        error_models.append({
            '产品型号': model,
            '产品名称': row['产品名称']
        })

if error_models:
    print(f"发现 {len(error_models)} 个产品型号包含日期格式：")
    for error in error_models[:10]:  # 只显示前10个错误
        print(f"  型号：{error['产品型号']}，名称：{error['产品名称']}")
    if len(error_models) > 10:
        print(f"  ... 还有 {len(error_models) - 10} 个类似错误")
else:
    print("未发现产品型号包含日期格式的错误")

# 检查产品型号是否有其他明显错误
print(f"\n检查产品型号是否有其他明显错误：")
error_count = 0
valid_models = []
for index, row in all_products_df.iterrows():
    model = str(row['产品型号'])
    # 检查是否有明显不合理的型号
    if len(model) > 20 or (len(model) > 10 and model.isdigit()):
        error_count += 1
    else:
        valid_models.append(model)

print(f"发现 {error_count} 个可能有问题的产品型号")
print(f"有效产品型号示例：{list(set(valid_models[:10]))}")  # 显示前10个唯一的有效型号

print("\n" + "=" * 60)

# 检查数值字段是否合理
print("检查数值字段合理性...")
value_query = """
SELECT p.规格_KG, p.单价, p.数量_件, p.金额
FROM products p
JOIN customers c ON p.客户ID = c.customer_id
WHERE c.客户名称 = '七彩乐园';
"""

value_df = pd.read_sql_query(value_query, conn)

# 单价合理性检查
valid_price_count = value_df[(value_df['单价'] > 0) & (value_df['单价'] < 1000)].shape[0]
print(f"单价在合理范围（0-1000）的产品数量：{valid_price_count}/{len(value_df)}")

# 规格合理性检查
valid_spec_count = value_df[(value_df['规格_KG'] > 0) & (value_df['规格_KG'] < 500)].shape[0]
print(f"规格在合理范围（0-500）的产品数量：{valid_spec_count}/{len(value_df)}")

# 数量合理性检查
valid_quantity_count = value_df[(value_df['数量_件'] > 0) & (value_df['数量_件'] < 100)].shape[0]
print(f"数量在合理范围（0-100）的产品数量：{valid_quantity_count}/{len(value_df)}")

# 金额合理性检查
valid_amount_count = value_df[(value_df['金额'] > 0) & (value_df['金额'] < 100000)].shape[0]
print(f"金额在合理范围（0-100000）的产品数量：{valid_amount_count}/{len(value_df)}")

# 关闭数据库连接
conn.close()

print("\n" + "=" * 60)
print("验证完成！")