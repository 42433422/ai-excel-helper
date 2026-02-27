import sys
sys.path.insert(0, '.')

from shipment_excel_sync import FixedTemplateSyncManager

# 创建同步管理器
sync = FixedTemplateSyncManager(r'templates\七彩乐园.xlsx', '25出货')

print(f"Excel路径: {sync.excel_path}")
print(f"工作表: {sync.worksheet}")
print(f"最大行数: {sync.worksheet.max_row}")
print()

# 查找最后数据行
last_row = sync.find_last_data_row()
print(f"最后数据行: {last_row}")
print()

# 测试写入
products = [{
    'name': 'PE白底漆',
    'model': '9803',
    'quantity_tins': 10,
    'spec': 28.0,
    'unit_price': 10.0,
    'quantity_kg': 280.0,
    'amount': 2800.0
}]

print("开始写入...")
result = sync.insert_records('26-0100071A', '2026-01-30', products)
print(f"写入结果: {result}")
print()

# 重新加载检查
print("重新检查Excel...")
wb = sync.workbook
ws = wb['25出货']
print(f"新的最大行数: {ws.max_row}")

# 检查新写入的行
for row in range(max(1, ws.max_row - 3), ws.max_row + 1):
    a = ws.cell(row=row, column=1).value
    b = ws.cell(row=row, column=2).value
    c = ws.cell(row=row, column=3).value
    f = ws.cell(row=row, column=6).value
    g = ws.cell(row=row, column=7).value
    h = ws.cell(row=row, column=8).value
    print(f'行{row}: A={a} B={b} C={c} F={f} G={g} H={h}')

wb.close()
