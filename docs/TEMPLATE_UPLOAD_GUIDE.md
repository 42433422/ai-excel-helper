# 模板创建功能使用指南

## 概述

模板创建功能允许用户上传 Excel、Word 文档或商标图片，系统自动解析并生成可复用的模板。

## API 端点

### 1. 上传并创建模板

**端点**: `POST /api/templates/upload`

**请求参数**:
- `file` (multipart/form-data): 上传的文件
- `type` (string): 模板类型 (`excel`, `word`, `logo`)
- `name` (string, 可选): 模板名称
- `description` (string, 可选): 模板描述
- `created_by` (string, 可选): 创建者标识

**示例 (curl)**:
```bash
# 上传 Excel 模板
curl -X POST "http://localhost:8000/api/templates/upload" \
  -F "file=@/path/to/quote_template.xlsx" \
  -F "type=excel" \
  -F "name=报价单模板 v1" \
  -F "description=标准报价单模板"

# 上传 Word 模板
curl -X POST "http://localhost:8000/api/templates/upload" \
  -F "file=@/path/to/contract_template.docx" \
  -F "type=word" \
  -F "name=合同模板"

# 上传商标
curl -X POST "http://localhost:8000/api/templates/upload" \
  -F "file=@/path/to/logo.png" \
  -F "type=logo" \
  -F "name=公司 Logo"
```

**响应示例**:
```json
{
  "template_id": "uuid-string",
  "name": "报价单模板 v1",
  "type": "excel",
  "status": "parsed",
  "fields": [
    {
      "field_name": "product_name",
      "field_type": "string",
      "display_name": "产品名称",
      "required": false,
      "mapping_config": {
        "sheet": "报价单",
        "column": 1
      }
    }
  ],
  "metadata": {
    "sheets": [...],
    "placeholders": ["customer_name", "quote_date"]
  },
  "created_at": "2026-04-12T10:00:00Z"
}
```

### 2. 获取模板列表

**端点**: `GET /api/templates`

**查询参数**:
- `type` (string, 可选): 按类型过滤
- `status` (string, 可选): 按状态过滤
- `limit` (integer, 可选): 返回数量限制 (默认 100)
- `offset` (integer, 可选): 分页偏移 (默认 0)

**示例**:
```bash
curl "http://localhost:8000/api/templates?type=excel&limit=10"
```

### 3. 获取模板详情

**端点**: `GET /api/templates/{template_id}`

**示例**:
```bash
curl "http://localhost:8000/api/templates/uuid-string"
```

### 4. 更新模板信息

**端点**: `PUT /api/templates/{template_id}`

**请求体**:
```json
{
  "name": "新模板名称",
  "description": "更新后的描述",
  "status": "active"
}
```

**示例**:
```bash
curl -X PUT "http://localhost:8000/api/templates/uuid-string" \
  -H "Content-Type: application/json" \
  -d '{"name": "新名称", "status": "active"}'
```

### 5. 更新模板字段配置

**端点**: `PUT /api/templates/{template_id}/fields`

**请求体**:
```json
[
  {
    "field_name": "customer_name",
    "field_type": "string",
    "display_name": "客户名称",
    "required": true,
    "sort_order": 1
  }
]
```

### 6. 获取模板预览

**端点**: `POST /api/templates/{template_id}/preview`

**示例**:
```bash
curl -X POST "http://localhost:8000/api/templates/uuid-string/preview"
```

### 7. 删除模板

**端点**: `DELETE /api/templates/{template_id}`

**示例**:
```bash
curl -X DELETE "http://localhost:8000/api/templates/uuid-string"
```

## 支持的模板类型

### Excel 模板 (.xlsx, .xlsm)
- 自动识别工作表和表格区域
- 提取表头和字段定义
- 推断数据类型（文本、数字、日期等）
- 识别占位符 `{{field_name}}`
- 识别必填字段（包含"必填"、"*"等标记）

### Word 模板 (.docx)
- 提取文档结构和段落
- 识别表格和表头
- 提取占位符：
  - `{{field_name}}`
  - `{%field_name%}`
  - `${field_name}`
  - `[field_name]`
- 识别标题样式

### 商标图片 (.png, .jpg, .jpeg, .gif, .svg)
- 自动存储和关联
- 生成缩略图
- 支持常见图片格式

## 字段类型推断

系统会根据表头自动推断字段类型：

| 类型 | 识别关键词 |
|------|-----------|
| `date` | 日期、date、时间、time |
| `number` | 金额、价格、单价、总价、price、amount、cost |
| `integer` | 数量、qty、count、num |
| `phone` | 电话、手机、contact、phone |
| `email` | 邮箱、email、@ |
| `string` | 默认类型 |

## 模板状态

- `pending`: 已上传，等待解析
- `parsed`: 已解析，等待确认
- `active`: 已激活，可使用
- `deprecated`: 已废弃
- `deleted`: 已删除（软删除）

## 文件限制

- **最大文件大小**: 10MB
- **支持的文件类型**:
  - Excel: .xlsx, .xlsm
  - Word: .docx
  - Logo: .png, .jpg, .jpeg, .gif, .svg

## 错误处理

API 返回标准 HTTP 状态码：

- `200`: 成功
- `201`: 创建成功
- `400`: 请求参数错误
- `404`: 模板不存在
- `500`: 服务器内部错误

**错误响应示例**:
```json
{
  "detail": "不支持的文件类型，允许：.xlsx, .xlsm"
}
```

## 数据库

模板元数据存储在 `templates.db` SQLite 数据库中，包含以下表：

- `templates`: 模板基本信息
- `template_fields`: 模板字段定义
- `template_versions`: 模板版本历史

## 安全考虑

- 文件类型白名单验证
- MIME 类型校验
- 文件大小限制
- 路径遍历防护
- 文件存储在隔离目录

## 示例代码

### Python 客户端示例

```python
import requests

# 上传 Excel 模板
files = {'file': open('quote_template.xlsx', 'rb')}
data = {
    'type': 'excel',
    'name': '报价单模板',
    'description': '标准报价单模板'
}

response = requests.post(
    'http://localhost:8000/api/templates/upload',
    files=files,
    data=data
)

if response.status_code == 201:
    result = response.json()
    print(f"模板 ID: {result['template_id']}")
    print(f"识别的字段数：{len(result['fields'])}")
```

### JavaScript 客户端示例

```javascript
// 上传模板
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('type', 'excel');
formData.append('name', '报价单模板');

fetch('http://localhost:8000/api/templates/upload', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => {
  console.log('模板 ID:', data.template_id);
  console.log('字段:', data.fields);
});
```

## 最佳实践

1. **模板设计**: 在 Excel/Word 中使用清晰的表头和命名
2. **占位符**: 使用 `{{field_name}}` 格式标记需要填充的位置
3. **字段验证**: 上传后检查自动识别的字段，必要时手动调整
4. **版本管理**: 定期备份重要模板
5. **测试**: 在正式使用前测试模板填充效果

## 故障排除

### 问题：上传失败，提示"文件类型不支持"
**解决**: 确保文件扩展名在允许列表中，检查 MIME 类型

### 问题：解析后字段数量为 0
**解决**: 确保 Excel 有明确的表头行，Word 有清晰的表格结构

### 问题：占位符未被识别
**解决**: 使用标准格式 `{{field_name}}`，避免特殊字符

### 问题：大文件上传超时
**解决**: 减小文件大小或增加服务器超时设置

## 开发信息

- **模块位置**: `backend/template_upload.py`, `backend/template_api.py`
- **解析器**: `backend/excel_template_parser.py`, `backend/word_template_parser.py`
- **数据库模型**: `backend/template_database.py`
- **测试**: `backend/tests/test_template_upload.py`

## 更新日志

### v1.0.0 (2026-04-12)
- 初始版本
- 支持 Excel、Word、Logo 上传
- 自动字段识别和类型推断
- 完整的 CRUD API
- 单元测试覆盖
