# 图片上传 API 修复计划

## 问题诊断

### 错误信息
```
2026-03-21 23:40:41,805 - xcagi.http - INFO - POST /api/upload/temp -> 405 (1ms)
2026-03-21 23:40:41,805 - werkzeug - INFO - 127.0.0.1 - - [21/Mar/2026 23:40:41] "POST /api/upload/temp HTTP/1.1" 405 -
```

### 问题原因
- HTTP 405 错误表示请求方法不被允许
- `/api/upload/temp` 路由可能：
  1. 不存在
  2. 存在但不支持 POST 方法
  3. 路由配置错误

## 解决步骤

### 步骤 1: 检查现有上传路由
- 搜索代码库中所有与 upload 相关的路由
- 确认 `/api/upload/temp` 是否已定义
- 检查路由支持的方法（GET/POST/PUT/DELETE）

### 步骤 2: 创建或修复上传路由
如果路由不存在，创建新的上传路由文件：
- 文件路径：`app/routes/upload.py`
- 路由前缀：`/api/upload`
- 支持的方法：POST
- 功能：接收文件上传，保存到临时目录，返回文件路径

### 步骤 3: 实现临时文件上传处理
实现 `POST /api/upload/temp` 端点：
```python
@upload_bp.route('/temp', methods=['POST'])
def upload_temp():
    # 1. 检查是否有文件
    # 2. 验证文件类型（图片）
    # 3. 生成唯一文件名
    # 4. 保存到临时目录
    # 5. 返回文件路径
```

### 步骤 4: 注册路由
在 `app/routes/__init__.py` 中：
- 导入 upload_bp
- 注册蓝图到应用
- 添加到路由分组

### 步骤 5: 创建临时目录
- 路径：`e:\FHD\XCAGI\uploads\temp`
- 确保目录存在且有写入权限
- 配置临时文件清理策略

### 步骤 6: 测试上传功能
使用 curl 或 Python 脚本测试：
```bash
curl -X POST http://localhost:5000/api/upload/temp \
  -F "file=@test_image.png"
```

预期响应：
```json
{
  "success": true,
  "file_path": "uploads/temp/xxx.png",
  "filename": "test_image.png"
}
```

### 步骤 7: 前端联调
- 确认前端上传代码正确
- 测试完整的图片上传流程
- 验证从上传图片到生成标签的完整流程

## 技术细节

### 文件上传配置
```python
app.config['UPLOAD_FOLDER'] = 'uploads/temp'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
```

### 文件验证
- 检查文件扩展名
- 检查 MIME 类型
- 限制文件大小
- 生成安全的文件名

### 临时文件管理
- 设置文件过期时间（如 24 小时）
- 定期清理过期文件
- 防止磁盘空间耗尽

## 完成标准

- [ ] 上传路由创建完成
- [ ] POST /api/upload/temp 可用
- [ ] 文件验证逻辑完善
- [ ] 临时目录配置正确
- [ ] 测试上传成功
- [ ] 前端可以正常上传图片
- [ ] 完整的标签生成流程可用

## 预计时间
- 路由实现：15 分钟
- 文件处理逻辑：20 分钟
- 测试调试：15 分钟
- **总计：50 分钟**
