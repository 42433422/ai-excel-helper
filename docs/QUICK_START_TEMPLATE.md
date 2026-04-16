# 快速启动指南

## 环境准备

### 1. 安装依赖
```bash
cd e:\FHD
pip install -r requirements.txt
```

### 2. 启动后端服务
```bash
# 方式 1: 使用 uvicorn 直接启动
uvicorn backend.http_app:app --reload --host 0.0.0.0 --port 8000

# 方式 2: 使用 Python 模块启动
python -m uvicorn backend.http_app:app --reload
```

服务将在 http://localhost:8000 启动

## 快速测试

### 方式 1: 使用演示脚本（推荐）
```bash
# 确保后端服务已启动
python scripts/demo_template_upload.py
```

演示脚本将自动：
- 创建示例 Excel 和 Word 模板
- 上传到后端
- 展示解析结果
- 演示 CRUD 操作

### 方式 2: 使用 curl 命令
```bash
# 1. 上传 Excel 模板
curl -X POST "http://localhost:8000/api/templates/upload" \
  -F "file=@/path/to/your/template.xlsx" \
  -F "type=excel" \
  -F "name=测试模板"

# 2. 获取模板列表
curl "http://localhost:8000/api/templates"

# 3. 获取模板详情（替换 {template_id}）
curl "http://localhost:8000/api/templates/{template_id}"
```

### 方式 3: 访问 API 文档
浏览器打开：http://localhost:8000/docs

在 Swagger UI 中可以直接测试所有 API 端点。

## 创建测试模板

### Excel 模板示例
1. 打开 Excel
2. 在第一行添加表头：产品名称、型号、数量、单价
3. 添加几行示例数据
4. 在某个单元格添加占位符：`{{customer_name}}`
5. 保存为 `.xlsx` 文件

### Word 模板示例
1. 打开 Word
2. 添加标题和段落
3. 在段落中添加占位符：`{{customer_name}}`, `{{date}}`
4. 插入一个表格，添加表头和数据
5. 保存为 `.docx` 文件

## 验证功能

### 检查数据库
```bash
# 查看 SQLite 数据库
python -c "from backend.template_database import get_session, Template; s=get_session(); print(f'Templates: {s.query(Template).count()}')"
```

### 检查上传目录
上传的文件保存在：
```
e:\FHD\uploads\templates\
├── excel\
├── word\
└── logo\
```

### 运行单元测试
```bash
python -m pytest backend/tests/test_template_upload.py -v
```

## 常见问题

### Q: 服务启动失败
**A**: 检查端口是否被占用
```bash
# Windows
netstat -ano | findstr :8000

# 修改端口
uvicorn backend.http_app:app --reload --port 8001
```

### Q: 上传失败
**A**: 检查：
- 文件类型是否支持（.xlsx, .xlsm, .docx, .png, .jpg 等）
- 文件大小是否超过 10MB
- 文件是否损坏

### Q: 解析后字段为空
**A**: 确保：
- Excel 有明确的表头行
- Word 有清晰的表格结构
- 使用标准的占位符格式 `{{field_name}}`

### Q: 数据库不存在
**A**: 数据库会在首次运行时自动创建，位置：
```
e:\FHD\424\templates.db
```
或当前工作目录。

## 环境变量配置

可选的环境变量：

```bash
# 工作区根目录
set WORKSPACE_ROOT=e:\FHD

# 数据库目录
set FHD_DB_DIR=e:\FHD\424

# CORS 配置
set CORS_ALLOW_ORIGINS=http://localhost:3000,http://localhost:8080

# API 密钥（可选）
set FHD_API_KEYS=your-secret-key-here
```

## 下一步

1. **查看完整文档**: [docs/TEMPLATE_UPLOAD_GUIDE.md](./TEMPLATE_UPLOAD_GUIDE.md)
2. **查看实施总结**: [docs/TEMPLATE_IMPLEMENTATION_SUMMARY.md](./TEMPLATE_IMPLEMENTATION_SUMMARY.md)
3. **前端集成**: 将上传按钮集成到现有界面
4. **自定义开发**: 根据业务需求调整解析逻辑

## 支持

如有问题，请查看：
- API 文档：http://localhost:8000/docs
- 测试日志：运行测试时的详细输出
- 源代码注释：各模块中的文档字符串

---
*最后更新：2026-04-12*
