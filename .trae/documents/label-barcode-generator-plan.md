# 条码生成器增强计划

## 目标
在 label-template-generator skill 中增加条形码生成功能，使生成的标签模板能够自动创建与数据对应的条形码。

## 需求分析

### 当前问题
- 生成的标签模板中，条形码区域只是占位符（空矩形）
- 用户需要手动提供条形码图片
- 无法根据标签数据（如货号、码段）动态生成条形码

### 解决方案
集成条形码生成库，根据标签数据自动生成对应的条形码。

## 实现步骤

### 1. 添加条形码生成依赖
- ✅ 安装 `python-barcode` 或 `barcode` 库
- ✅ 支持多种条码格式：EAN-13, Code128, Code39 等
- ✅ 添加可选依赖说明到文档

### 2. 实现条形码生成功能
- ✅ 创建 `BarcodeGenerator` 类
- ✅ 实现 `generate_barcode(data, barcode_type)` - 生成条形码
- ✅ 实现 `save_barcode(filename, data, options)` - 保存为图片
- ✅ 实现 `get_barcode_types()` - 获取支持的条码类型

### 3. 集成到标签生成器
- ✅ 在 `LabelTemplateGenerator` 类中添加 `_draw_barcode()` 方法
- ✅ 自动识别条码数据源（货号、码段组合等）
- ✅ 支持自定义条码下方文本

### 4. 增强字段识别
- ✅ 在 OCR 识别阶段检测条形码区域
- ✅ 识别条形码类型和位置
- ✅ 提取条形码下方的文本信息

### 5. 生成代码增强
- ✅ 生成的代码包含条形码生成配置
- ✅ 条码数据映射规则
- ✅ 条码样式选项（尺寸、颜色、位置）

### 6. 使用示例
- ✅ 自动生成条码示例
- ✅ 自定义条码数据示例
- ✅ EAN-13 条码示例

## 前端功能实现

### 1. 从图片生成标签模板
- ✅ 添加"📷 从图片生成"按钮
- ✅ 图片上传区域（支持拖拽）
- ✅ 图片预览功能
- ✅ 自动生成类名

### 2. 配置选项
- ✅ 模板类名输入框
- ✅ OCR 识别开关
- ✅ 生成进度显示

### 3. 结果展示
- ✅ 代码查看器（带语法高亮）
- ✅ 字段列表表格
- ✅ 字段类型标记

### 4. 保存为模板
- ✅ 保存对话框
- ✅ 模板名称输入
- ✅ 模板分类选择（Excel/标签打印）
- ✅ 模板类型选择
- ✅ 备注说明输入
- ✅ 保存到服务器

### 5. 后端 API
- ✅ `POST /api/skills/generate-label-template` - 生成标签模板
- ✅ `POST /api/excel/templates/create` - 创建模板

## 技术选型

### 条形码库选择
**推荐：`python-barcode`**
- ✅ 纯 Python 实现，无需外部依赖
- ✅ 支持多种条码格式（EAN, Code128, Code39 等）
- ✅ 可直接生成 SVG 或与 PIL 集成生成 PNG
- ✅ 文档完善，易于使用
- ✅ 已安装：`pip install python-barcode`

### 支持的条码格式
1. ✅ **EAN-13**: 商品零售条码（最常用）
2. ✅ **Code128**: 工业应用，支持字母数字
3. ✅ **Code39**: 字母数字，较老标准
4. ✅ **UPC-A**: 北美商品条码
5. ✅ **ITF**: 运输包装

## 代码结构

### 新增文件
```
app/services/skills/label-template-generator/
├── label_template_generator.py  ✅ (修改)
├── barcode_generator.py         ✅ (新增)
├── __init__.py                  ✅ (修改)
└── SKILL.md                     ✅ (修改)
```

### 修改现有代码
1. ✅ **label_template_generator.py**
   - 添加条形码生成导入
   - 在 `_draw_fields()` 中集成条码绘制
   - 新增 `_draw_barcode()` 方法

2. ✅ **__init__.py**
   - 导出 `BarcodeGenerator` 类

3. ✅ **SKILL.md**
   - 更新功能说明
   - 添加条形码生成示例
   - 更新依赖列表

4. ✅ **TemplatePreviewView.vue**
   - 添加从图片生成按钮
   - 实现生成向导弹窗
   - 添加保存对话框

5. ✅ **excel_templates.py**
   - 添加 `create_template` API

## 测试计划

### 测试用例
1. ✅ 测试生成 EAN-13 条码
2. ✅ 测试生成 Code128 条码
3. ✅ 测试自动组合条码数据
4. ✅ 测试条码位置和尺寸
5. ✅ 测试条码下方文本显示
6. ✅ 测试无 OCR 时的条码生成
7. ✅ 测试图片上传功能
8. ✅ 测试模板保存功能

### 验证标准
- ✅ 生成的条码可被扫描枪识别
- ✅ 条码尺寸适合标签布局
- ✅ 条码下方文本清晰可读
- ✅ 支持自定义条码数据
- ✅ 前端界面友好易用
- ✅ 模板保存成功并可查看

## 文档更新

### SKILL.md 更新内容
1. ✅ 添加条形码生成示例
2. ✅ 更新依赖列表（添加 python-barcode）
3. ✅ 说明条码数据配置方式
4. ✅ 提供条码类型选择指南

### 新增文档
- ✅ `docs/label-template-generator-feature.md` - 完整功能说明

## 完成标准

- [x] 实现 BarcodeGenerator 类
- [x] 集成到 LabelTemplateGenerator
- [x] 支持至少 3 种条码格式（EAN-13, Code128, Code39）
- [x] 更新 SKILL.md 文档
- [x] 编写使用示例
- [x] 通过测试验证
- [x] 代码已保存到输出文件
- [x] 前端界面实现
- [x] 后端 API 实现
- [x] 保存为模板功能
- [x] 模板分类选择

## 时间估算
- 实现 BarcodeGenerator: 30 分钟 ✅
- 集成到标签生成器：30 分钟 ✅
- 测试和调试：20 分钟 ✅
- 文档更新：10 分钟 ✅
- 前端界面实现：40 分钟 ✅
- 后端 API 实现：20 分钟 ✅
- **总计：约 150 分钟**

## 使用示例

### 1. 从图片生成标签模板
```python
# 前端操作：
1. 点击"📷 从图片生成"按钮
2. 上传标签图片
3. 点击"🚀 生成模板"
4. 查看生成的代码和字段
5. 点击"✓ 保存为模板"
6. 填写模板名称和分类
7. 确认保存
```

### 2. 使用生成的模板
```python
from app.infrastructure.documents.generated_templates.shoe_label_generator import ShoeLabelGenerator

generator = ShoeLabelGenerator(output_dir="./labels")

data = {
    "product_name": "XX 运动鞋",
    "color": "白色",
    "item_number": "1635",
    "code_segment": "00001",
    "grade": "合格品",
    "standard": "QB/T4331-2013",
    "price": "199",
    "auto_barcode": True  # 自动生成条形码
}

filename = generator.generate_label(data, "ORDER-001", 1)
print(f"生成的标签：{filename}")
```

### 3. 自定义条形码数据
```python
data = {
    "product_name": "XX 运动鞋",
    "barcode_data": "163500001",  # 直接提供条码数据
    "barcode_type": "code128"
}

filename = generator.generate_label(data, "ORDER-001", 1)
```

## 总结

✅ **所有功能已实现完成！**

主要成就：
1. 条形码生成功能完整实现
2. 前端图片上传和生成界面友好
3. 模板保存和管理功能完善
4. 支持多种条码格式
5. 自动识别字段和条码数据
6. 完整的文档和示例
