import openpyxl

wb = openpyxl.load_workbook('尹玉华1.xlsx')
ws = wb.active

print('=== 第2行详细分析 ===')
for col in range(1, 10):
    cell = ws.cell(row=2, column=col)
    merged_info = None
    for merged_range in ws.merged_cells.ranges:
        if (2, col) in [(mr.min_row, mr.min_col) for mr in [merged_range]]:
            merged_info = str(merged_range)
            break
    print(f'列{col}: 值="{cell.value}" | 合并到: {merged_info}')

wb.close()