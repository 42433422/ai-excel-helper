# 模板导出功能验证指南

## 快速验证（推荐）

### 方法 1: 运行自动化测试脚本
```bash
cd e:\FHD
python scripts/test_template_export.py
```

**预期结果**:
```
总计：6/6 测试通过
🎉 所有测试通过！模板导出功能正常工作。
```

### 方法 2: 运行单元测试
```bash
python -m pytest backend/tests/test_template_upload.py -v
```

**预期结果**:
```
17 passed in 2-3s
```

### 方法 3: 手动 API 测试

#### 1. 启动后端服务
```bash
uvicorn backend.http_app:app --reload
```

#### 2. 访问 API 文档
浏览器打开：http://localhost:8000/docs

#### 3. 测试上传端点
在 Swagger UI 中找到 `/api/templates/upload` 端点：
- 点击 "Try it out"
- 选择文件（.xlsx 或 .docx）
- 设置 type 为 "excel" 或 "word"
- 点击 "Execute"

**预期响应**:
```json
{
  "template_id": "uuid-string",
  "name": "文件名",
  "type": "excel",
  "status": "parsed",
  "fields": [...],
  "metadata": {...}
}
```

## 功能验证清单

### ✅ 上传功能
- [ ] 可以上传 Excel 文件（.xlsx, .xlsm）
- [ ] 可以上传 Word 文件（.docx）
- [ ] 可以上传图片文件（.png, .jpg 等）
- [ ] 文件类型验证正常工作
- [ ] 文件大小限制正常工作（10MB）

### ✅ 解析功能
- [ ] Excel 模板正确识别工作表
- [ ] Excel 模板正确识别表格和表头
- [ ] Excel 模板正确提取占位符 `{{field_name}}`
- [ ] Word 模板正确解析文档结构
- [ ] Word 模板正确提取占位符

### ✅ 填充功能
- [ ] Excel 模板可以用数据填充
- [ ] Word 模板可以用数据填充
- [ ] 占位符被正确替换
- [ ] 生成输出文件
- [ ] 返回正确的输出路径

### ✅ 导出功能
- [ ] 数据可以导出为 Excel 格式
- [ ] 导出的文件包含正确的数据
- [ ] 导出的文件包含正确的表头
- [ ] 输出文件可以下载

### ✅ 数据库功能
- [ ] 模板元数据正确保存
- [ ] 字段信息正确保存
- [ ] 可以查询模板列表
- [ ] 可以查询模板详情

## 手动测试步骤

### 测试 1: Excel 模板上传和解析

1. **创建测试模板**
   - 打开 Excel
   - 在第一行添加表头：产品名称、型号、数量、单价
   - 在第二行添加占位符：`{{product_name}}`、`{{model_number}}` 等
   - 保存为 `test_template.xlsx`

2. **上传模板**
   ```bash
   curl -X POST "http://localhost:8000/api/templates/upload" \
     -F "file=@test_template.xlsx" \
     -F "type=excel" \
     -F "name=测试模板"
   ```

3. **验证响应**
   - 检查 `status` 是否为 "parsed"
   - 检查 `fields` 是否包含识别的字段
   - 检查 `placeholders` 是否包含提取的占位符

### 测试 2: Excel 模板填充

1. **准备测试数据**
   ```json
   {
     "customer_name": "测试客户",
     "quote_date": "2026-04-12",
     "product_name": "测试产品",
     "model_number": "MODEL-001",
     "quantity": "100",
     "unit_price": "10.5"
   }
   ```

2. **调用填充接口**
   ```bash
   curl -X POST "http://localhost:8000/api/templates/upload" \
     -F "file=@test_template.xlsx" \
     -F "type=excel" \
     -F "name=测试模板"
   
   # 获取 template_id 后
   curl -X POST "http://localhost:8000/api/templates/{template_id}/preview"
   ```

3. **验证输出**
   - 检查是否返回 `output_path`
   - 下载输出文件
   - 打开文件验证占位符是否被正确替换

### 测试 3: 数据导出

1. **准备数据**
   ```json
   [
     {"产品名称": "产品 A", "型号": "M001", "数量": 100, "单价": 10.5},
     {"产品名称": "产品 B", "型号": "M002", "数量": 200, "单价": 20.5}
   ]
   ```

2. **调用导出接口**
   使用 API 文档中的 `/api/templates/upload` 端点，但 action 设置为 "export"

3. **验证导出文件**
   - 检查文件是否存在
   - 打开文件验证数据是否正确

## 常见问题排查

### 问题 1: 上传失败
**症状**: 返回 400 错误，提示文件类型不支持

**排查步骤**:
1. 检查文件扩展名是否为 .xlsx, .xlsm, .docx 等
2. 检查文件大小是否超过 10MB
3. 检查 MIME 类型是否正确

### 问题 2: 解析后字段为空
**症状**: 解析成功但 fields 数组为空

**排查步骤**:
1. 确保 Excel 有明确的表头行
2. 确保表头单元格有内容
3. 检查是否使用了正确的占位符格式 `{{field_name}}`

### 问题 3: 填充后占位符未替换
**症状**: 输出文件中占位符仍然存在

**排查步骤**:
1. 检查数据键名是否与占位符名称匹配
2. 检查占位符格式是否正确
3. 确认模板文件没有被损坏

### 问题 4: 数据库查询失败
**症状**: 返回数据库错误

**排查步骤**:
1. 检查数据库文件是否存在
2. 运行 `init_db()` 初始化数据库
3. 检查 SQLAlchemy 连接配置

## 性能验证

### 测试大文件
```bash
# 创建一个包含 1000 行数据的 Excel 文件
python scripts/create_large_test_file.py

# 测试上传和解析
time curl -X POST "http://localhost:8000/api/templates/upload" \
  -F "file=@large_template.xlsx" \
  -F "type=excel"
```

**预期性能**:
- 100 行以内：< 500ms
- 1000 行以内：< 2s
- 10MB 文件：< 5s

## 验证报告

完成验证后，填写以下清单：

### 功能完整性
- [ ] 上传功能正常
- [ ] 解析功能正常
- [ ] 填充功能正常
- [ ] 导出功能正常
- [ ] 数据库功能正常

### 稳定性
- [ ] 连续测试 10 次无失败
- [ ] 并发上传 5 个文件无错误
- [ ] 大文件处理正常

### 性能
- [ ] 响应时间符合要求
- [ ] 内存使用合理
- [ ] 文件存储正常

### 文档
- [ ] API 文档准确
- [ ] 错误信息清晰
- [ ] 示例代码可用

## 结论

如果所有验证项目都通过，则模板导出功能已准备就绪，可以投入使用。

---

*最后更新：2026-04-12*
