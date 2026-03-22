---
name: "excel-toolkit"
description: "Excel文件查看工具，用于分析结构、内容、合并单元格和位置信息。Invoke when user wants to view, analyze or inspect Excel files."
---

# Excel Toolkit

Excel文件综合查看工具，支持分析文件结构、内容、合并单元格和格式信息。

## 使用方法

### Python代码方式

```python
import openpyxl
from openpyxl import load_workbook

wb = load_workbook(r'文件路径.xlsx')

for sheet_name in wb.sheetnames:
    ws = wb[sheet_name]
    print(f'=== Sheet: {sheet_name} ===')
    print(f'Dimensions: {ws.dimensions}')
    print(f'Max row: {ws.max_row}, Max col: {ws.max_column}')
    print()

    for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
        for cell in row:
            if cell.value is not None:
                print(f'{cell.coordinate}: {repr(cell.value)}')
    print()
```

### 获取合并单元格信息

```python
wb = load_workbook(r'文件路径.xlsx')
ws = wb.active

print('=== 合并单元格 ===')
for merge in ws.merged_cells.ranges:
    print(f'合并范围: {merge} - 起始单元格: {merge.min_row},{merge.min_col}')
```

### 获取单元格样式信息

```python
wb = load_workbook(r'文件路径.xlsx')
ws = wb.active

for row in ws.iter_rows(min_row=1, max_row=min(10, ws.max_row)):
    for cell in row:
        if cell.value is not None:
            print(f'{cell.coordinate}: value={repr(cell.value)}, '
                  f'font={cell.font.name}, size={cell.font.size}, '
                  f'bold={cell.font.bold}, '
                  f'align={cell.alignment.horizontal}')
```

## 功能列表

| 功能 | 触发场景 |
|------|----------|
| 查看所有单元格内容 | 用户说"查看文件"、"查看内容" |
| 分析文件结构 | 用户说"分析结构"、"了解文件" |
| 获取合并单元格 | 用户说"合并单元格"、"哪些单元格合并了" |
| 获取样式信息 | 用户说"什么格式"、"字体大小" |

## 示例输出

对于"迎扬李总.xlsx"的输出：

```
Sheet names: ['迎扬电视墙']
=== Sheet: 迎扬电视墙 ===
Dimensions: A1:M255
Max row: 255, Max col: 13

A1: '中江博郡家私'
A3: ' 产 品 型 号'
D3: ' 产 品 名 称'
E3: '单价/元'
A4: 2269
D4: 'PU亮光荷花白色漆'
E4: 17
...
```
