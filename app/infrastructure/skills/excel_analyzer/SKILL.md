---
name: "excel-analyzer"
description: "Analyzes Excel templates to identify structure, styles, editable content, and formatting. Invoke when user asks to analyze, parse, or understand an Excel template layout."
---

# Excel Template Analyzer

This skill enables AI to analyze and parse Excel template files, extracting structural information, styles, and content types.

## When to Use This Skill

Invoke this skill when:
- User asks to analyze, parse, or understand an Excel template
- User wants to identify which cells are template content vs editable
- User needs to extract borders, merges, fonts, and other styles
- User wants to build or reconstruct an Excel template programmatically
- User asks "how does this Excel file work" or "what's in this spreadsheet"

## How to Use

### Python Module

Import and use the analyzer in your Python code:

```python
from excel_template_analyzer import analyze_template, analyze_to_json

# Analyze and get result as dict
result = analyze_template("path/to/file.xlsx")

# Analyze and save to JSON file
analyze_to_json("path/to/file.xlsx", "output.json")
```

### Command Line

```bash
python excel_template_analyzer.py -f input.xlsx -o output.json
```

Options:
- `-f, --file`: Excel file path (required)
- `-o, --output`: Output JSON file path
- `-s, --sheet`: Sheet name to analyze (default: first sheet)
- `-v, --verbose`: Verbose output mode

## Output Format

The analyzer returns a JSON structure with:

```json
{
  "file": "filename.xlsx",
  "sheet": "Sheet1",
  "structure": {
    "max_row": 26,
    "max_col": 13,
    "max_col_letter": "M"
  },
  "zones": [
    {"name": "header", "rows": [1,2,3], "type": "template", "description": "表头和标题区域"},
    {"name": "data", "rows": [4,5,6], "type": "editable", "description": "数据输入区域"},
    {"name": "summary", "rows": [19,20], "type": "template", "description": "汇总和签名区域"}
  ],
  "merged_cells": [
    {"range": "A1:J1", "min_row": 1, "max_row": 1, "min_col": 1, "max_col": 10, "purpose": "标题"}
  ],
  "editable_ranges": [
    {"range": "A4:C18", "min_row": 4, "max_row": 18, "min_col": 1, "max_col": 3, "description": "产品型号输入区"}
  ],
  "cells": {
    "A1": {
      "address": "A1", "row": 1, "col": 1,
      "value": "Title",
      "type": "template",
      "is_merged": true,
      "merged_range": "A1:J1",
      "style": {
        "font_name": "宋体",
        "font_size": 24.0,
        "font_bold": false,
        "font_color": "FF000000",
        "alignment_horizontal": "center",
        "alignment_vertical": "center",
        "border_style": "thin,thin,thin,thin"
      }
    },
    "A4": {
      "address": "A4", "row": 4, "col": 1,
      "value": "2269",
      "type": "editable"
    },
    "G4": {
      "address": "G4", "row": 4, "col": 7,
      "value": null,
      "type": "formula",
      "formula": "=E4*F4"
    }
  }
}
```

## Cell Types

| Type | Description |
|------|-------------|
| `template` | Fixed template content (titles, headers, labels) |
| `editable` | User-editable data cells |
| `formula` | Excel formulas |
| `empty` | Empty cells |

## Content Zones

| Zone | Type | Description |
|------|------|-------------|
| header | template | Title, company info, table headers |
| data | editable | Product/item rows for input |
| summary | template | Totals, signatures, notes |

## Style Properties

Each cell's style includes:
- **font_name**: Font family (e.g., "宋体")
- **font_size**: Font size in points
- **font_bold**: Whether font is bold
- **font_color**: Font color as hex string
- **fill_pattern**: Fill pattern type
- **fill_fg_color**: Foreground color
- **fill_bg_color**: Background color
- **alignment_horizontal**: Horizontal alignment (left, center, right)
- **alignment_vertical**: Vertical alignment (top, center, bottom)
- **border_style**: Border styles (e.g., "thin,thin,thin,thin")
- **number_format**: Number format string

## Example Analysis

For a delivery note template:

1. **Header zone** (rows 1-3): Title, company info, column headers
2. **Data zone** (rows 4-18): Product entries - columns A-C (product codes) and D-J (product details) are editable
3. **Summary zone** (rows 19-26): Totals, signature areas

This allows AI to:
- Understand which parts are fixed templates
- Know where to insert new data
- Replicate the format for new documents
- Validate input data locations
