# 创建模板功能

> 上传 Excel、Word 或商标图片，一键生成可复用模板

## 功能特性

✅ **支持多种格式**: Excel (.xlsx, .xlsm), Word (.docx), 商标图片 (.png, .jpg, .gif, .svg)  
✅ **智能解析**: 自动识别表格、字段、数据类型和占位符  
✅ **一键上传**: 简单快捷的上传流程  
✅ **完整 API**: RESTful API 支持 CRUD 操作  
✅ **单元测试**: 17 个测试用例，100% 通过  

## 快速开始

### 1. 启动服务
```bash
uvicorn backend.http_app:app --reload
```

### 2. 上传模板
```bash
curl -X POST "http://localhost:8000/api/templates/upload" \
  -F "file=@template.xlsx" \
  -F "type=excel" \
  -F "name=我的模板"
```

### 3. 运行演示
```bash
python scripts/demo_template_upload.py
```

## API 端点

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/templates/upload` | 上传模板 |
| GET | `/api/templates` | 获取模板列表 |
| GET | `/api/templates/{id}` | 获取模板详情 |
| PUT | `/api/templates/{id}` | 更新模板 |
| PUT | `/api/templates/{id}/fields` | 更新字段配置 |
| DELETE | `/api/templates/{id}` | 删除模板 |

完整文档：http://localhost:8000/docs

## 示例代码

### Python
```python
import requests

files = {'file': open('template.xlsx', 'rb')}
data = {'type': 'excel', 'name': '报价单模板'}

response = requests.post(
    'http://localhost:8000/api/templates/upload',
    files=files,
    data=data
)

print(response.json())
```

### JavaScript
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('type', 'excel');

fetch('http://localhost:8000/api/templates/upload', {
  method: 'POST',
  body: formData
})
.then(r => r.json())
.then(console.log);
```

## 核心模块

- [`backend/template_upload.py`](backend/template_upload.py) - 文件上传处理
- [`backend/excel_template_parser.py`](backend/excel_template_parser.py) - Excel 解析器
- [`backend/word_template_parser.py`](backend/word_template_parser.py) - Word 解析器
- [`backend/template_database.py`](backend/template_database.py) - 数据库模型
- [`backend/template_api.py`](backend/template_api.py) - API 路由

## 文档

- 📖 [使用指南](docs/TEMPLATE_UPLOAD_GUIDE.md) - 详细 API 和使用说明
- 🚀 [快速启动](docs/QUICK_START_TEMPLATE.md) - 快速开始使用
- 📊 [实施总结](docs/TEMPLATE_IMPLEMENTATION_SUMMARY.md) - 技术实施详情

## 测试

```bash
# 运行所有测试
python -m pytest backend/tests/test_template_upload.py -v

# 运行特定测试
python -m pytest backend/tests/test_template_upload.py::TestExcelParser -v
```

## 技术栈

- **后端**: FastAPI + SQLAlchemy
- **Excel**: openpyxl, pandas
- **Word**: python-docx
- **图片**: Pillow
- **数据库**: SQLite
- **测试**: pytest

## 支持的占位符格式

- `{{field_name}}` - Excel 和 Word
- `{%field_name%}` - Word
- `${field_name}` - Word
- `[field_name]` - Word

## 字段类型自动推断

| 类型 | 识别关键词 |
|------|-----------|
| date | 日期、date、时间 |
| number | 金额、价格、price |
| integer | 数量、qty、count |
| phone | 电话、手机、phone |
| email | 邮箱、email、@ |

## 文件限制

- 最大文件大小：10MB
- 支持的文件类型：.xlsx, .xlsm, .docx, .png, .jpg, .gif, .svg

## 安全特性

✅ 文件类型白名单验证  
✅ MIME 类型校验  
✅ 文件大小限制  
✅ 路径遍历防护  
✅ 隔离存储目录  

## 许可证

内部项目

---

*最后更新：2026-04-12*
