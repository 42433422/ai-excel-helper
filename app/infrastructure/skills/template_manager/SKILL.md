---
name: "template-manager"
description: "Excel模板管理工具，支持发货单、出货记录、产品列表、购买单位列表等各类模板。Invoke when user wants to manage templates, list templates, decompose template structure, or create new templates for export."
---

# Template Manager Skill

Excel模板管理工具，提供对系统中各类模板的查看、解析、创建和管理功能。

## 支持的模板类型

| 模板类型 | template_type | 说明 |
|----------|---------------|------|
| 发货单模板 | 发货单 | 发货单据模板 |
| 出货记录模板 | 出货记录 | 出货记录表单 |
| 产品列表模板 | 产品列表 | 产品数据导出模板 |
| 购买单位列表模板 | 购买单位列表 | 购买单位导出模板 |
| 标签模板 | 标签/label | 打印标签模板 |

## 功能概述

| 功能 | 说明 | 触发场景 |
|------|------|----------|
| 列出所有模板 | 获取系统中注册的所有模板 | "查看模板"、"有哪些模板" |
| 列出物理文件 | 列出templates目录下的实际模板文件 | "查看模板文件"、"模板存放位置" |
| 获取模板文件 | 下载或获取模板文件路径 | "获取模板"、"下载模板" |
| 分解模板 | 解析模板结构，提取表头和可编辑区域 | "分解模板"、"分析模板结构" |
| 创建模板 | 创建新的模板配置 | "创建模板"、"添加模板" |
| 按类型查询 | 按模板类型查询 | "发货单模板"、"产品列表模板" |
| 导出数据 | 使用模板导出数据 | "导出产品"、"导出购买单位" |

## 使用方法

### 1. 获取所有模板列表（系统注册的）

```python
from app.services.skills.template_manager import list_all_templates

templates = list_all_templates()
for t in templates:
    print(f"{t['id']} - {t['name']} ({t['template_type']})")
```

### 2. 列出物理模板文件（templates目录下的实际文件）

```python
from app.services.skills.template_manager import list_physical_template_files

files = list_physical_template_files()
for f in files:
    print(f"{f['filename']} -> {f['full_path']} ({f['size_bytes']} bytes)")
```

### 3. 获取指定模板文件的路径

```python
from app.services.skills.template_manager import get_template_file

info = get_template_file("发货单.xlsx")
if info:
    print(f"文件路径: {info['full_path']}")
```

### 4. 按类型获取模板

```python
from app.services.skills.template_manager import list_templates_by_type

# 发货单模板
templates = list_templates_by_type("发货单", active_only=True)

# 产品列表模板
templates = list_templates_by_type("产品列表", active_only=True)

# 购买单位列表模板
templates = list_templates_by_type("购买单位列表", active_only=True)

# 出货记录模板
templates = list_templates_by_type("出货记录", active_only=True)
```

### 5. 解析模板结构

```python
from app.services.skills.template_manager import decompose_template_file

result = decompose_template_file(
    file_path="E:/FHD/XCAGI/templates/发货单.xlsx",
    sheet_name="出货",
    sample_rows=5
)
```

### 6. 上传新模板

```python
import requests

with open('template.xlsx', 'rb') as f:
    response = requests.post(
        'http://localhost:5000/api/excel/upload',
        files={'excel_file': f}
    )
```

### 7. 导出产品数据（使用产品列表模板）

```python
from app.services.skills.template_manager import export_products_with_template

result = export_products_with_template(unit_name=None, keyword=None)
```

## 模板物理文件位置

系统中的实际模板文件存放在以下目录：

| 目录 | 路径 | 说明 |
|------|------|------|
| templates | `E:/FHD/XCAGI/templates/` | 主要模板存放目录 |
| temp_excel | `E:/FHD/XCAGI/temp_excel/` | 临时上传的Excel文件 |

### templates目录下现有的Excel文件

- `发货单.xlsx` - 发货单模板
- `七彩乐园.xlsx` - 七彩乐园模板
- `七彩乐园_备份.xlsx` - 七彩乐园备份
- `新建 XLSX 工作表 (2).xlsx` - 其他模板
- `尹玉华1 - 副本.xlsx` - 尹玉华模板副本
- `manual_product_template.xlsx` - 手动产品模板

## 模板数据结构

```json
{
  "id": "shipment",
  "name": "发货单模板",
  "filename": "发货单模板.xlsx",
  "template_type": "发货单",
  "category": "excel",
  "file_path": "/path/to/发货单模板.xlsx",
  "exists": true,
  "is_active": true
}
```

## 物理模板文件结构

```json
{
  "filename": "发货单.xlsx",
  "full_path": "E:/FHD/XCAGI/templates/发货单.xlsx",
  "directory": "templates",
  "size_bytes": 174519,
  "exists": true
}
```

## 分解模板输出

```json
{
  "success": true,
  "template": {
    "name": "发货单.xlsx",
    "sheet": "出货",
    "dimension": "A1:M26",
    "max_row": 26,
    "max_column": 13
  },
  "decomposition": {
    "header_row": 3,
    "editable_entries": [
      {"name": "产品型号", "column": "A", "column_index": 1},
      {"name": "产品名称", "column": "D", "column_index": 4}
    ],
    "amount_related_entries": [
      {"name": "金额", "column": "K", "column_index": 11}
    ],
    "sample_rows": [...],
    "merged_cells_count": 5
  }
}
```

## API接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/excel/templates` | GET | 获取模板列表 |
| `/api/excel/template/<id>/file` | GET | 下载模板文件 |
| `/api/excel/template/save` | POST | 保存模板 |
| `/api/excel/template/decompose` | POST | 分解模板 |
| `/api/excel/templates/by_type` | GET | 按类型获取模板 |
| `/api/excel/templates/default` | GET | 获取默认模板 |
| `/api/excel/upload` | POST | 上传Excel文件 |
| `/api/products/export.xlsx` | GET | 导出产品(产品列表模板) |