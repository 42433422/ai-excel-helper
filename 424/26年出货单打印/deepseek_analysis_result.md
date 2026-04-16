# DeepSeek Excel 结构分析报告

分析时间: 2026-04-02 20:00:20

## 原始数据摘要

分析文件数: 8

## 分析结果

```json
{
  "analysis_summary": {
    "total_files": 8,
    "total_sheets": 39,
    "unique_header_patterns": 15
  },
  "normalized_field_mapping": {
    "产品型号": ["产品型号", "产 品 型 号", "型号"],
    "产品名称": ["产品名称", "产 品 名 称", "名称"],
    "规格": ["规格", "规格/KG", "规格/KG"],
    "单价": ["单价", "单价/元", "现金价"],
    "数量": ["数量/件", "数量/KG"],
    "金额": ["金额/元", "金额总计", "金额合计"],
    "备注": ["备注", "备  注", "备 注"],
    "日期": ["日期"],
    "单号": ["单号"],
    "客户名": ["客户名"],
    "月份": ["月份"]
  },
  "template_types": [
    {
      "name": "出货明细表",
      "description": "详细的出货记录，包含日期、单号、产品信息、数量、金额等",
      "required_fields": ["产品型号", "产品名称", "数量", "单价", "金额"],
      "optional_fields": ["日期", "单号", "规格", "备注", "金额合计"],
      "example_files": ["宗南 - 副本.xlsx", "志泓 - 副本.xlsx", "七彩乐园.xlsx"],
      "example_sheets": ["出货", "25出货"]
    },
    {
      "name": "产品目录表",
      "description": "产品基本信息表，主要用于报价或产品清单",
      "required_fields": ["产品型号", "产品名称", "规格", "单价"],
      "optional_fields": ["备注"],
      "example_files": ["七彩乐园 - 副本.xlsx", "侯雪梅 - 副本.xlsx", "宗南 - 副本.xlsx"],
      "example_sheets": ["Sheet2", "报价", "Sheet1"]
    },
    {
      "name": "汇总统计表",
      "description": "金额汇总或回款记录表，包含总计金额",
      "required_fields": ["金额总计", "金额合计"],
      "optional_fields": ["销售金额", "实收款", "下欠款金额", "家具厂金额"],
      "example_files": ["2024曹林成鑫.xlsx", "侯雪梅 - 副本.xlsx", "新旺博旺 - 副本.xlsx"],
      "example_sheets": ["出货", "24回款", "24出货"]
    },
    {
      "name": "特殊格式表",
      "description": "非标准格式，可能是数据记录或混合内容",
      "required_fields": [],
      "optional_fields": ["客户名", "月份", "内", "外"],
      "example_files": ["侯雪梅 - 副本.xlsx"],
      "example_sheets": ["24年明细账", "出货记录"]
    }
  ],
  "field_aliases": {
    "TERM_EQUIVALENTS": {
      "product_code": ["产品型号", "产 品 型 号", "型号"],
      "product_name": ["产品名称", "产 品 名 称", "名称"],
      "specification": ["规格", "规格/KG"],
      "unit_price": ["单价", "单价/元", "现金价"],
      "quantity_piece": ["数量/件"],
      "quantity_kg": ["数量/KG"],
      "amount": ["金额/元", "金额总计", "金额合计"],
      "remark": ["备注", "备  注", "备 注"],
      "date": ["日期"],
      "order_no": ["单号"],
      "customer_name": ["客户名"],
      "month": ["月份"]
    }
  },
  "files_with_issues": [
    {
      "file": "新旺博旺 - 副本.xlsx",
      "sheet": "24出货",
      "issue": "表头异常，只有前几个字段有实际内容，后面大量空字段",
      "suggestion": "可能需要跳过前几行或使用特定行作为表头"
    },
    {
      "file": "侯雪梅 - 副本.xlsx",
      "sheet": "24年明细账",
      "issue": "表头重复（客户名、月份、内、外、备注出现两次）",
      "suggestion": "可能是合并单元格或双栏布局，需要特殊解析逻辑"
    },
    {
      "file": "2024曹林成鑫.xlsx",
      "sheet": "出货记录",
      "issue": "表头包含具体数据值（如'44964', '4号', 'CX903'等）",
      "suggestion": "该行可能不是真正的表头，需要检查实际数据起始行"
    }
  ],
  "recommendations": [
    {
      "category": "数据清洗",
      "suggestion": "统一字段名称，去除多余空格（如'备  注'改为'备注'）"
    },
    {
      "category": "单位处理",
      "suggestion": "将'数量/件'和'数量/KG'拆分为两个独立字段，或添加单位标识字段"
    },
    {
      "category": "模板识别",
      "suggestion": "根据前5-10行数据特征自动识别模板类型，应用对应的解析规则"
    },
    {
      "category": "异常处理",
      "suggestion": "对表头异常的文件，实现动态表头检测，或提供手动修正界面"
    },
    {
      "category": "数据验证",
      "suggestion": "检查必填字段是否为空，对缺失关键信息的行进行标记或跳过"
    },
    {
      "category": "性能优化",
      "suggestion": "对超大文件（如新旺博旺.xlsx）采用流式读取，避免内存溢出"
    }
  ]
}
```