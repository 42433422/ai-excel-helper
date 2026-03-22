# 📷 从图片生成标签模板 - 使用指南

## ✅ 功能已就绪

所有功能已经成功构建并测试通过！

## 🚀 快速开始

### 1. 访问页面
打开浏览器访问：**http://localhost:5000/console?view=excel**

### 2. 找到功能按钮
在页面顶部工具栏找到 **📷 从图片生成** 按钮（绿色）

### 3. 使用流程

#### 步骤 1: 上传图片
- 点击上传区域或拖拽图片
- 支持 PNG, JPG, JPEG 格式
- 实时预览上传的图片

#### 步骤 2: 配置选项
- **模板类名**：自动生成（可修改）
- **启用 OCR**：勾选（如已安装 Tesseract）

#### 步骤 3: 生成模板
点击 **🚀 生成模板** 按钮

#### 步骤 4: 查看结果
- **生成的代码**：Python 标签模板代码
- **识别到的字段**：字段列表和类型

#### 步骤 5: 保存为模板
点击 **✓ 保存为模板**，填写：
- **模板名称**：例如 "运动鞋标签模板" ✏️
- **模板分类**：选择 "标签打印" 或 "Excel" 📂
- **模板类型**：选择 "标签"
- **备注说明**：可选

点击 **✓ 确认保存**

## 📊 测试结果

### ✅ 测试 1: 条形码生成器
```
✓ BarcodeGenerator 创建成功
  支持的条码类型：['ean13', 'ean8', 'code128', 'code39', 'upca', 'itf']
✓ 条形码生成成功 (数据：163500001)
  图片尺寸：(400, 70)
```

### ✅ 测试 2: 标签模板生成器
```
✓ Label Template Generator Skill 加载成功
  技能名称：label_template_generator
  技能描述：从图片生成标签模板代码...
✓ 生成成功！
  代码长度：4999 字符
  输出文件：test_shoe_label_generator.py
```

### ✅ 测试 3: 使用生成的模板
```
✓ 生成的模板类加载成功
✓ 生成器实例创建成功
✓ 标签生成成功：TEST-001_第 1 项_XX_运动鞋.png
```

## 🎯 核心功能

### 1. 条形码生成 ✅
- 支持 EAN-13, Code128, Code39 等多种格式
- 自动组合条码数据（货号 + 码段）
- 可自定义条码数据

### 2. 字段识别 ✅
- 自动识别固定标签和可变数据
- 支持常见中文标签模式
- 智能字段映射

### 3. 模板分类管理 ✅
- 支持 Excel 和标签打印两种分类
- 可自定义模板名称
- 完整的模板元数据

## 📁 生成的文件

### 代码文件
- `test_shoe_label_generator.py` - 生成的标签模板代码
- `test_barcode.png` - 测试条形码图片
- `TEST-001_第 1 项_XX_运动鞋.png` - 生成的标签图片

### 代码示例
```python
class TestShoeLabelGenerator:
    def __init__(self, output_dir=None):
        self.width = 502
        self.height = 621
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
    
    def generate_label(self, data, order_number="", label_index=1):
        # 生成标签图片（包含条形码）
        pass
```

## 🔧 技术栈

- **Python 库**: Pillow, python-barcode
- **前端**: Vue.js, Element UI
- **后端**: Flask, python-barcode
- **OCR**: pytesseract (可选)

## 📝 API 端点

### 生成标签模板
```
POST /api/skills/generate-label-template
```

### 创建模板
```
POST /api/excel/templates/create
```

## 💡 使用提示

1. **图片质量**: 清晰的图片有助于更好的识别效果
2. **OCR 功能**: 如未安装 Tesseract，将使用回退方案
3. **条形码**: python-barcode 已安装，可正常生成
4. **字段识别**: 支持常见的中文标签模式
5. **模板保存**: 保存后可在模板列表中查看和管理

## 🎉 成功标志

✅ 图片上传成功  
✅ 代码生成成功  
✅ 字段识别成功  
✅ 条形码生成成功  
✅ 模板保存成功  
✅ 在模板列表中可见  

## 📖 更多文档

- 详细功能说明：`docs/label-template-generator-feature.md`
- 实现计划：`.trae/documents/label-barcode-generator-plan.md`
- 测试脚本：`run_label_generator_tests.py`

---

**祝你使用愉快！** 🎊

如有问题，请查看控制台日志或联系开发团队。
