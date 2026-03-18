# Vue + Flask 集成方案说明文档

## 项目概述

本项目是将原有的 AI 助手控制台 HTML/JavaScript 应用重构为 Vue 3 单页应用（SPA），并提供与 Flask 后端的集成方案。

## 主要功能集成总结

### 1. 聊天功能 (Task 7)
- **ChatView.vue** 已完全实现，包含：
  - 消息发送和接收功能
  - 快速操作按钮（查产品、客户列表、出货单、库存预警、打印标签等）
  - 消息历史管理和会话记录
  - 新建对话和历史对话加载

### 2. 各页面数据操作 (Task 8)
已实现以下页面的完整 CRUD 操作：
- **产品管理** (ProductsView.vue)：
  - 加载产品列表
  - 添加、编辑、删除产品
  - 批量删除
  - 导出价格表
  - 搜索和筛选功能
  
- **原材料仓库** (MaterialsView.vue)：
  - 加载原材料列表
  - 添加、编辑、删除原材料
  - 批量删除
  - 库存预警显示
  - 分类筛选和搜索
  
- **客户管理** (CustomersView.vue)：
  - 加载客户列表
  - 导入/导出 Excel
  - 批量删除
  - 客户统计显示

### 3. 专业模式 (Task 9)
- 创建了 **ProMode.vue** 组件
- 包含完整的专业模式 UI 和动画效果
- 数字雨效果
- Jarvis 风格界面
- 专业模式开关已集成到侧边栏

### 4. 文件上传下载预览 (Task 10)
- 所有浮动窗口元素已集成到 App.vue
- 包含：
  - 文件上传入口 (fileUploadEntry)
  - 导入窗口 (importFloatWindow)
  - 商标导出窗口 (labelsExportWindow)
  - 打印面板 (printPanelWindow)
  - 标签漂浮预览 (labelFloatPreviews)
  - 标签预览模态框 (labelPreviewModal)
  - 进度面板 (progressPanel)
  - 预览窗口 (previewFloatWindow)
  - 过渡遮罩 (transitionOverlay)

## 生产构建步骤

### 前置要求
- Node.js (建议版本 16.x 或更高)
- npm 或 yarn 包管理器

### 构建步骤

1. **安装依赖**
   ```bash
   cd ai-assistant-vue
   npm install
   ```

2. **开发模式运行（可选）**
   ```bash
   npm run dev
   ```
   这将启动开发服务器，默认在 http://localhost:5173

3. **生产构建**
   ```bash
   npm run build
   ```
   构建产物将生成在 `dist` 目录中

## Flask 集成方案

### 方案一：静态文件服务（推荐）

1. **将 Vue 构建产物复制到 Flask 项目**
   ```
   AI助手/
   ├── app_api.py
   ├── static/
   │   ├── css/
   │   ├── js/
   │   └── vue-build/          # 新建目录
   │       ├── index.html
   │       └── assets/
   └── templates/
   ```

2. **修改 Flask 应用配置**

   在 Flask 应用文件（如 app_api.py）中添加以下路由：

   ```python
   from flask import Flask, send_from_directory, jsonify, request
   import os

   app = Flask(__name__, static_folder='static', static_url_path='/static')

   # Vue 应用的构建目录
   VUE_BUILD_DIR = os.path.join(os.path.dirname(__file__), 'static', 'vue-build')

   # 提供 Vue 构建的静态文件
   @app.route('/')
   def index():
       return send_from_directory(VUE_BUILD_DIR, 'index.html')

   @app.route('/<path:path>')
   def serve_vue_static(path):
       # 先尝试从 Vue 构建目录提供文件
       if os.path.exists(os.path.join(VUE_BUILD_DIR, path)):
           return send_from_directory(VUE_BUILD_DIR, path)
       # 如果不存在，继续处理其他路由
       return send_from_directory(VUE_BUILD_DIR, 'index.html')

   # 保持原有的 API 路由不变
   @app.route('/api/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
   def api_proxy(path):
       # 原有的 API 处理逻辑
       pass
   ```

3. **配置 Vite 构建输出**

   修改 `vite.config.js`，确保构建路径正确：

   ```javascript
   import { defineConfig } from 'vite'
   import vue from '@vitejs/plugin-vue'

   export default defineConfig({
     plugins: [vue()],
     base: '/',
     build: {
       outDir: 'dist',
       assetsDir: 'assets',
       emptyOutDir: true
     }
   })
   ```

### 方案二：使用 Flask 模板（保持现有结构）

如果希望保持现有的 Flask 模板结构，可以：

1. **将 Vue 组件作为独立页面嵌入**
2. **修改 index.html 引用 Vue 构建的 JS/CSS**
3. **保持原有的 API 路由完全不变**

### 方案三：反向代理（生产环境推荐）

使用 Nginx 或类似的反向代理服务器：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Vue 静态文件
    location / {
        root /path/to/ai-assistant-vue/dist;
        try_files $uri $uri/ /index.html;
    }

    # API 请求代理到 Flask
    location /api/ {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 静态资源（CSS、JS、图片等）
    location /static/ {
        proxy_pass http://127.0.0.1:5000;
    }
}
```

## API 接口兼容性

Vue 应用使用的 API 接口与原 HTML 应用完全兼容：

- `/api/ai/chat-unified` - 统一聊天接口
- `/api/conversations/*` - 对话管理
- `/api/products/*` - 产品管理
- `/api/materials/*` - 原材料管理
- `/api/customers/*` - 客户管理
- `/api/orders/*` - 订单/出货单管理
- `/api/print/*` - 标签打印
- `/api/media/*` - 媒体文件（新增）

## 部署清单

### 开发环境
- [ ] Node.js 安装
- [ ] npm install 执行成功
- [ ] npm run dev 正常启动
- [ ] API 代理配置（如需）

### 生产环境
- [ ] npm run build 成功执行
- [ ] dist 目录内容完整
- [ ] Flask 路由配置正确
- [ ] 静态文件权限设置
- [ ] API 端点可访问
- [ ] CORS 配置（如需要）

## 注意事项

1. **保持 CSS 类名**：所有原有的 CSS 类名都已保留，确保样式正确
2. **API_BASE 配置**：Vue 应用中的 API_BASE 默认为空（相对路径），与 Flask 路由兼容
3. **本地存储**：会话 ID 等数据使用 localStorage 存储，与原应用一致
4. **渐进式迁移**：可以逐步迁移各个页面，Vue 应用与原 HTML 应用可以共存

## 下一步建议

1. 测试各个功能模块
2. 根据实际需求调整 UI/UX
3. 添加错误处理和加载状态优化
4. 配置生产环境的日志和监控
5. 进行性能优化和代码分割
