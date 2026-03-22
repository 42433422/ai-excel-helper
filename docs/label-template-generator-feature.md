# 从图片生成标签模板功能说明

## 功能概述

通过上传图片，自动生成对应的 Python 标签模板代码，支持条形码生成、字段识别等功能。

## 实现内容

### 1. 后端 API

#### 1.1 生成标签模板代码
**端点**: `POST /api/skills/generate-label-template`

**请求参数**:
```json
{
  "image_path": "图片文件路径",
  "class_name": "LabelTemplateGenerator",  // 可选，默认类名
  "enable_ocr": true  // 可选，是否启用 OCR
}
```

**响应**:
```json
{
  "success": true,
  "code": "生成的 Python 代码",
  "analysis": {...},  // 图片分析结果
  "ocr_result": {     // OCR 识别结果（如果启用）
    "fields": [
      {
        "field_key": "product_name",
        "label": "品名",
        "value": "XX 运动鞋",
        "type": "fixed_label"
      }
    ]
  }
}
```

#### 1.2 创建模板
**端点**: `POST /api/excel/templates/create`

**请求参数**:
```json
{
  "name": "运动鞋标签模板",
  "category": "label_print",  // 或 "excel"
  "template_type": "标签",
  "description": "模板描述",
  "code": "Python 代码",
  "source": "generated",
  "metadata": {
    "class_name": "ShoeLabelGenerator",
    "fields": [...]
  }
}
```

### 2. 前端界面

#### 2.1 从图片生成按钮
- 位置：模板预览页面顶部工具栏
- 样式：绿色按钮，带相机图标 📷
- 功能：打开图片上传和生成弹窗

#### 2.2 生成流程弹窗

**步骤 1: 上传图片**
- 支持点击选择或拖拽上传
- 实时预览图片
- 自动从文件名生成类名

**步骤 2: 配置选项**
- 模板类名（可编辑）
- OCR 识别开关

**步骤 3: 生成结果**
- 代码查看器展示生成的 Python 代码
- 字段列表展示识别到的字段
- 字段类型标记（固定标签/可变数据）

**步骤 4: 保存为模板**
- 点击"✓ 保存为模板"按钮
- 弹出保存对话框

#### 2.3 保存对话框

**必填字段**:
- 模板名称（文本输入）
- 模板分类（下拉选择）
  - 标签打印
  - Excel

**可选字段**:
- 模板类型（下拉选择）
  - 标签
  - 通用
  - 自定义
- 备注说明（文本域）

**操作按钮**:
- 取消
- ✓ 确认保存

### 3. 生成的代码功能

生成的 Python 标签模板代码包含：

#### 3.1 字段定义
```python
self.fields = {
    "product_name": {
        "label": "品名",
        "default_value": "XX 运动鞋",
        "type": "fixed_label",
        "editable": True
    },
    "item_number": {
        "label": "货号",
        "default_value": "1635",
        "type": "fixed_label",
        "editable": True
    },
    ...
}
```

#### 3.2 条形码生成
支持两种模式：
1. **自动生成**: `auto_barcode: True` - 组合货号 + 码段
2. **自定义数据**: `barcode_data: "163500001"`

#### 3.3 使用方法
```python
generator = ShoeLabelGenerator(output_dir="./labels")

data = {
    "product_name": "XX 运动鞋",
    "item_number": "1635",
    "code_segment": "00001",
    "auto_barcode": True  # 自动生成条形码
}

filename = generator.generate_label(data, "ORDER-001", 1)
```

### 4. 文件存储

#### 4.1 代码文件
- 目录：`app/infrastructure/documents/generated_templates/`
- 命名：`tpl_YYYYMMDDHHMMSS_模板名.py`

#### 4.2 模板索引
- 文件：`templates.json`
- 位置：同上目录
- 内容：模板元数据列表

### 5. 使用流程

1. **访问模板预览页面**
   - 导航到模板管理界面

2. **点击"📷 从图片生成"**
   - 打开生成向导弹窗

3. **上传标签图片**
   - 拖拽或点击选择图片文件
   - 支持 PNG, JPG, JPEG 格式

4. **配置生成选项**
   - 确认或修改类名
   - 选择是否启用 OCR

5. **生成模板代码**
   - 点击"🚀 生成模板"按钮
   - 等待分析和生成完成

6. **查看生成结果**
   - 查看生成的 Python 代码
   - 查看识别到的字段列表

7. **保存为模板**
   - 点击"✓ 保存为模板"按钮
   - 填写模板名称和分类
   - 点击"✓ 确认保存"

8. **使用模板**
   - 在模板列表中查看新模板
   - 可以编辑、删除或打开使用

### 6. 技术特性

- ✅ 支持 OCR 文字识别（需安装 Tesseract）
- ✅ 自动识别固定标签和可变数据
- ✅ 支持多种条形码格式（EAN-13, Code128, Code39）
- ✅ 智能字段映射和类型识别
- ✅ 响应式上传界面
- ✅ 代码语法高亮显示
- ✅ 字段分类表格展示
- ✅ 模板分类管理

### 7. 依赖安装

```bash
# 必需
pip install Pillow

# 可选：OCR 功能
pip install pytesseract
# 安装 Tesseract OCR 引擎
# Windows: https://github.com/tesseract-ocr/tesseract

# 可选：条形码生成
pip install python-barcode
```

### 8. 注意事项

1. **OCR 识别**: 如果未安装 Tesseract，将使用回退方案（基于预设模式）
2. **条形码**: 如果未安装 python-barcode，生成占位符矩形
3. **图片质量**: 清晰的图片有助于更好的 OCR 识别效果
4. **字段识别**: 目前支持常见的中文标签模式，可自定义扩展

### 9. 扩展开发

可以通过修改以下文件来增强功能：

- `barcode_generator.py`: 添加新的条形码格式支持
- `label_template_generator.py`: 优化字段识别逻辑
- `TemplatePreviewView.vue`: 改进前端界面和交互
