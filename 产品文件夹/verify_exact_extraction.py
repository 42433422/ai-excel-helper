import sqlite3
import pandas as pd
import re
import openpyxl

# 连接数据库
conn = sqlite3.connect('customer_products_final_corrected.db')

print("验证精确提取的产品信息...")
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

# 专门检查七彩乐园的产品信息
print("详细检查七彩乐园的产品信息：")

query = """
SELECT p.产品型号, p.产品名称, p.规格_KG, p.单价, p.数量_件, p.数量_KG, p.金额, p.单号
FROM products p
JOIN customers c ON p.客户ID = c.customer_id
WHERE c.客户名称 = '七彩乐园'
LIMIT 20;
"""

七彩乐园_products = pd.read_sql_query(query, conn)
print("七彩乐园提取的产品信息示例（前20条）：")
print(七彩乐园_products)

# 检查七彩乐园的原始数据，对比提取结果
print("\n" + "=" * 60)
print("对比原始Excel数据与提取结果：")

# 加载原始Excel文件
file_path = 'e:\\女娲1号\\发货单\\七彩乐园.xlsx'
wb = openpyxl.load_workbook(file_path)
ws = wb['25出货']

print("\n原始Excel数据（行3-15）：")
for row_idx in range(3, 16):  # 从行3开始，对应原始数据的第3行
    row = ws[row_idx]
    row_values = []
    for cell in row:
        row_values.append(cell.value)
    print(f"行 {row_idx}: {row_values[:12]}")

print("\n提取结果对比（前10条）：")
print(七彩乐园_products.head(10))

# 检查是否有明显的错误
print("\n" + "=" * 60)
print("检查提取结果中的明显错误：")

# 检查产品型号是否包含日期或其他错误格式
print("\n检查产品型号是否包含日期格式：")
date_pattern = r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日'
error_models = []
for index, row in 七彩乐园_products.iterrows():
    model = str(row['产品型号'])
    if re.match(date_pattern, model):
        error_models.append({
            '产品型号': model,
            '产品名称': row['产品名称']
        })

if error_models:
    print(f"发现 {len(error_models)} 个产品型号包含日期格式：")
    for error in error_models:
        print(f"  型号：{error['产品型号']}，名称：{error['产品名称']}")
else:
    print("未发现产品型号包含日期格式的错误")

# 检查产品型号是否有其他明显错误
print(f"\n检查产品型号是否有其他明显错误：")
problematic_models = []
for index, row in 七彩乐园_products.iterrows():
    model = str(row['产品型号'])
    # 检查是否为纯数字且长度过长（可能是日期或其他错误）
    if model.isdigit() and len(model) > 5:
        problematic_models.append(model)
    # 检查是否包含明显的非型号字符
    elif any(char in model for char in ['元', 'kg', 'KG', '件', '数量', '规格', '单价', '金额']):
        problematic_models.append(model)

if problematic_models:
    print(f"发现 {len(problematic_models)} 个可能有问题的产品型号：")
    # 去重并显示前10个
    unique_problems = list(set(problematic_models))[:10]
    for problem in unique_problems:
        print(f"  - {problem}")
else:
    print("未发现明显有问题的产品型号")

# 显示有效产品型号示例
print(f"\n有效产品型号示例：")
valid_models = []
for index, row in 七彩乐园_products.iterrows():
    model = str(row['产品型号'])
    if model and not re.match(date_pattern, model):
        valid_models.append(model)
        if len(valid_models) >= 10:
            break

print(valid_models)

# 检查数值字段合理性
print(f"\n检查数值字段合理性：")
# 单价合理性检查
valid_price_count = 七彩乐园_products[(七彩乐园_products['单价'] > 0) & (七彩乐园_products['单价'] < 1000)].shape[0]
print(f"单价在合理范围（0-1000）的产品数量：{valid_price_count}/{len(七彩乐园_products)}")

# 规格合理性检查
valid_spec_count = 七彩乐园_products[(七彩乐园_products['规格_KG'] > 0) & (七彩乐园_products['规格_KG'] < 500)].shape[0]
print(f"规格在合理范围（0-500）的产品数量：{valid_spec_count}/{len(七彩乐园_products)}")

# 数量合理性检查
valid_quantity_count = 七彩乐园_products[(七彩乐园_products['数量_件'] >= 0) & (七彩乐园_products['数量_件'] < 100)].shape[0]
print(f"数量在合理范围（0-100）的产品数量：{valid_quantity_count}/{len(七彩乐园_products)}")

# 金额合理性检查
valid_amount_count = 七彩乐园_products[(七彩乐园_products['金额'] > 0) & (七彩乐园_products['金额'] < 100000)].shape[0]
print(f"金额在合理范围（0-100000）的产品数量：{valid_amount_count}/{len(七彩乐园_products)}")

# 关闭数据库连接和工作簿
conn.close()
wb.close()

print("\n" + "=" * 60)
print("验证完成！")