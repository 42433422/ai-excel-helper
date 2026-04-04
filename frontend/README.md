# XCAGI v4.0 AI 员工前端

> 🤖 Vue 3 + Vite 构建的现代化 AI 员工前端界面

[![Vue](https://img.shields.io/badge/Vue-3.3-brightgreen.svg)](https://vuejs.org/)
[![Vite](https://img.shields.io/badge/Vite-4.4-brightgreen.svg)](https://vitejs.dev/)
[![Pinia](https://img.shields.io/badge/Pinia-3.0-yellowgreen.svg)](https://pinia.vuejs.org/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-blue.svg)](https://www.typescriptlang.org/)

## 🌟 功能特性

### AI 员工交互
- 🤖 **智能对话界面** - 与 AI 员工自然语言交互
- 🗣️ **TTS 语音播报** - 实时语音反馈
- 💬 **多轮对话** - 上下文理解和连续对话
- 🎯 **意图可视化** - 实时显示 AI 识别的意图

### 单据管理
- 📊 **Excel 单据处理** - 上传、解析、确认
- 🏷️ **标签打印** - 模板编辑、批量打印
- 📦 **出货管理** - 创建、查询、发货
- ✅ **收货管理** - 收货确认、库存更新

### 数据管理
- 📦 **产品管理** - CRUD、导入导出
- 👥 **客户管理** - 客户信息、价格体系
- 📚 **物料管理** - 原材料仓库管理
- 📈 **数据可视化** - 业务数据图表

### 微信集成
- 💬 **微信消息** - 消息接收和回复
- 👥 **联系人同步** - 自动同步微信联系人
- 🤖 **自动任务** - 基于微信消息创建任务

### Pro 模式（高级功能）
- 🎨 **Jarvis 界面** - 钢铁侠风格监控界面
- 📊 **实时监控** - 系统状态、性能指标
- 🎯 **快捷操作** - 悬浮面板、快速查询
- 🌈 **粒子特效** - 科技感视觉效果

## 🚀 快速开始

### 环境要求

- Node.js 18+ 
- npm 9+
- 后端服务运行中（http://localhost:5000）

### 安装依赖

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 或使用国内镜像
npm install --registry=https://registry.npmmirror.com
```

### 开发模式

```bash
# 启动开发服务器
npm run dev

# 访问 http://localhost:5173
```

### 生产构建

```bash
# 构建生产版本
npm run build

# 预览构建结果
npm run preview
```

### Docker 部署

```bash
# 从项目根目录启动
docker-compose up -d --build frontend

# 访问 http://localhost
```

## 📁 项目结构

```
frontend/
├── public/                 # 静态资源
│   └── static/
│       ├── css/           # CSS 样式
│       │   ├── animations/ # 动画效果
│       │   ├── components/ # 组件样式
│       │   └── base.css   # 基础样式
│       └── js/            # JavaScript 模块
│           ├── core/      # 核心工具
│           └── modules/   # 功能模块
├── src/
│   ├── api/               # API 接口层
│   │   ├── auth.ts       # 认证 API
│   │   ├── chat.ts       # 对话 API
│   │   ├── customers.ts  # 客户 API
│   │   ├── orders.ts     # 订单 API
│   │   ├── products.ts   # 产品 API
│   │   └── system.ts     # 系统 API
│   ├── assets/            # 资源文件
│   ├── components/        # Vue 组件
│   │   ├── pro-feature-widget/  # Pro 功能组件
│   │   ├── pro-mode/           # Pro 模式组件
│   │   ├── template/           # 模板组件
│   │   └── ...
│   ├── composables/       # 组合式函数
│   │   ├── useJarvisChat.ts
│   │   ├── useProMode.ts
│   │   └── ...
│   ├── router/            # 路由配置
│   ├── stores/            # Pinia 状态管理
│   │   ├── jarvisChat.ts
│   │   ├── proMode.ts
│   │   └── ...
│   ├── styles/            # 全局样式
│   │   ├── animations/    # 动画样式
│   │   └── variables.css  # CSS 变量
│   ├── types/             # TypeScript 类型
│   ├── utils/             # 工具函数
│   ├── views/             # 页面视图
│   │   ├── ChatView.vue   # 对话页面
│   │   ├── OrdersView.vue # 订单页面
│   │   ├── ProductsView.vue
│   │   └── ...
│   ├── App.vue           # 根组件
│   └── main.ts           # 入口文件
├── index.html            # HTML 模板
├── package.json          # 项目配置
├── vite.config.js        # Vite 配置
└── tsconfig.json         # TypeScript 配置
```

## 🎨 核心组件

### AI 对话组件

```vue
<template>
  <ChatView />
</template>

<script setup>
import ChatView from '@/views/ChatView.vue'
</script>
```

### Pro 模式组件

```vue
<template>
  <ProModeOverlay />
  <JarvisCore />
</template>

<script setup>
import ProModeOverlay from '@/components/pro-mode/ProModeOverlay.vue'
import JarvisCore from '@/components/pro-mode/JarvisCore.vue'
</script>
```

### 数据表格组件

```vue
<template>
  <DataTable 
    :columns="columns"
    :data="products"
    :pagination="true"
  />
</template>

<script setup>
import DataTable from '@/components/DataTable.vue'
</script>
```

## 🔧 配置说明

### API 代理配置

编辑 `vite.config.js`:

```javascript
export default {
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true
      }
    }
  }
}
```

### 环境变量

创建 `.env.local`:

```bash
# API 基础地址
VITE_API_BASE_URL=http://localhost:5000

# 启用 Pro 模式
VITE_PRO_MODE_ENABLED=true

# TTS 语音配置
VITE_TTS_ENABLED=true
```

## 🧪 测试

```bash
# 运行单元测试
npm test

# 运行测试并生成覆盖率
npm run test:coverage

# 运行 E2E 测试
npm run test:e2e
```

### 测试技术栈

- **Vitest**: 单元测试框架
- **@vue/test-utils**: Vue 组件测试工具
- **jsdom**: DOM 模拟环境
- **Playwright**: E2E 测试框架

## 📦 构建优化

### 代码分割

```javascript
// 路由懒加载
const ChatView = () => import('@/views/ChatView.vue')
const OrdersView = () => import('@/views/OrdersView.vue')
```

### Tree Shaking

```javascript
// 按需导入
import { Button, Table } from 'element-plus'
```

### 压缩优化

```javascript
// vite.config.js
export default {
  build: {
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    }
  }
}
```

## 🎯 Pro 模式

### 启用 Pro 模式

```javascript
// 在设置中启用 Pro Mode
// 或使用快捷键：Ctrl + Shift + P
```

### Pro 模式功能

- **Jarvis 监控界面**: 钢铁侠风格 UI
- **数字雨特效**: 科技感背景动画
- **粒子效果**: 能量粒子动画
- **代码光环**: 图标旋转光环
- **能量条**: 工作进度可视化

## 🌐 API 集成

### 认证流程

```typescript
import { authApi } from '@/api/auth'

// 登录
const { token } = await authApi.login({
  username: 'admin',
  password: 'password'
})

// 存储 token
localStorage.setItem('token', token)
```

### AI 对话

```typescript
import { chatApi } from '@/api/chat'

// 发送消息
const response = await chatApi.sendMessage({
  message: '帮我创建出货单',
  context: { customerId: '123' }
})

// 处理响应
console.log(response.intent) // 识别的意图
console.log(response.reply)  // AI 回复
```

### 单据处理

```typescript
import { orderApi } from '@/api/orders'

// 上传 Excel
const result = await orderApi.uploadExcel(file)

// 创建出货单
const order = await orderApi.createShipment({
  customerId: '123',
  products: [...]
})
```

## 🎨 样式定制

### CSS 变量

```css
/* src/styles/variables.css */
:root {
  --primary-color: #409EFF;
  --success-color: #67C23A;
  --warning-color: #E6A23C;
  --danger-color: #F56C6C;
  --info-color: #909399;
}
```

### 主题定制

```css
/* 暗黑主题 */
.dark-theme {
  --bg-color: #1a1a1a;
  --text-color: #ffffff;
  --border-color: #333333;
}
```

## 📊 性能指标

### 构建大小

```
Total Size: ~500 KB (gzipped)
- Vendor: ~350 KB
- App: ~150 KB
```

### 加载时间

```
First Contentful Paint: ~0.8s
Time to Interactive: ~1.2s
Lighthouse Score: 95+
```

## 🔐 安全建议

1. **Token 存储**: 使用 localStorage 存储 JWT Token
2. **XSS 防护**: Vue 自动转义，避免使用 v-html
3. **CSRF 防护**: 使用 SameSite Cookie 策略
4. **内容安全**: 配置 CSP 头

## 🤝 贡献指南

### 开发流程

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码规范

```bash
# 代码格式化
npm run lint

# 类型检查
npm run type-check
```

## 📚 学习资源

- [Vue 3 文档](https://vuejs.org/)
- [Vite 文档](https://vitejs.dev/)
- [Pinia 文档](https://pinia.vuejs.org/)
- [TypeScript 文档](https://www.typescriptlang.org/)
- [Element Plus 文档](https://element-plus.org/)

## 📄 许可证

本项目采用 **AGPL-3.0** 许可证。

---

**版本**: v4.0  
**最后更新**: 2026-03-25  
**作者**: XCAGI Team
