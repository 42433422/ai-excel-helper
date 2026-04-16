# AI Assistant Vue 前端

Vue 3 + Vite 开发的前端项目。

## 功能列表

- AI 对话界面
- 产品管理
- 客户管理
- 订单管理
- 打印管理
- 微信联系人管理
- 原材料仓库
- 工具表

## 快速开始

```bash
# 安装依赖
cd ai-assistant-vue
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build

# 预览生产版本
npm run preview
```

## 测试

```bash
# 运行单元测试
npm test

# 运行测试并生成覆盖率报告
npm run test:coverage

# 运行 E2E 测试
npm run test:e2e
```

## 测试技术栈

- **Vitest**: 单元测试框架
- **@vue/test-utils**: Vue 组件测试工具
- **jsdom**: DOM 模拟环境
- **Playwright**: E2E 测试框架

## 项目结构

```
src/
├── api/              # API 接口模块
│   ├── chat.js
│   ├── customers.js
│   ├── orders.js
│   ├── print.js
│   ├── products.js
│   └── wechat.js
├── components/       # Vue 组件
├── composables/      # Vue Composable
├── utils/           # 工具函数
└── views/           # 页面视图
```

## API 配置

前端 API 默认连接 `http://localhost:5000`，如需修改请编辑 `src/api/index.js`。
