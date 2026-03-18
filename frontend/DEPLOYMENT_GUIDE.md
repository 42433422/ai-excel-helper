# AI 智能助手 Vue 应用生产构建与部署指南

## 前置条件

在开始之前，请确保您的系统已安装以下软件：

- **Node.js** (推荐版本 16.x 或更高)
- **npm** (随 Node.js 一起安装)

您可以通过以下命令检查是否已安装：

```bash
node --version
npm --version
```

如果未安装，请从 [Node.js 官网](https://nodejs.org/) 下载并安装。

## 步骤 1: 安装 Vue 项目依赖

进入 Vue 项目目录并安装依赖：

```bash
cd e:\FHD\ai-assistant-vue
npm install
```

## 步骤 2: 生产构建

执行生产构建命令：

```bash
npm run build
```

构建成功后，您将看到类似以下输出：

```
vite v4.4.5 building for production...
✓ 21 modules transformed.
dist/index.html                  0.45 kB
dist/assets/index.abc123.js     123.45 kB
dist/assets/index.def456.css      45.67 kB
✓ built in 2.345s
```

构建产物将生成在 `e:\FHD\ai-assistant-vue\dist` 目录中。

## 步骤 3: 复制构建产物到 Flask 应用

将 `dist` 目录的所有内容复制到 Flask 应用的模板目录：

```bash
# 使用 PowerShell
Copy-Item -Path "e:\FHD\ai-assistant-vue\dist\*" -Destination "e:\FHD\AI助手\templates\vue-dist\" -Recurse -Force
```

或者手动复制：
1. 打开 `e:\FHD\ai-assistant-vue\dist` 文件夹
2. 全选所有文件和文件夹
3. 复制到 `e:\FHD\AI助手\templates\vue-dist\` 文件夹

## 步骤 4: 修改 Flask 路由配置

编辑 `e:\FHD\AI助手\routes\pages.py` 文件，做以下修改：

### 修改 1: index() 函数
找到以下代码：

```python
@pages_bp.route('/')
def index():
    """首页 → 直接使用 AI助手/templates/ai_assistant_console.html（专业版控制台，静态资源来自 AI助手/static）"""
    return send_from_directory(
        os.path.join(BASE_DIR, 'templates'),
        'ai_assistant_console.html',
        mimetype='text/html'
    )
```

替换为：

```python
@pages_bp.route('/')
def index():
    """首页 → 使用 Vue 应用"""
    return send_from_directory(
        os.path.join(BASE_DIR, 'templates', 'vue-dist'),
        'index.html',
        mimetype='text/html'
    )
```

### 修改 2: ai_assistant() 函数
找到以下代码：

```python
@pages_bp.route('/ai_assistant')
def ai_assistant():
    """AI助手专业版页面"""
    return send_from_directory(
        os.path.join(BASE_DIR, 'templates'),
        'ai_assistant_console.html',
        mimetype='text/html'
    )
```

替换为：

```python
@pages_bp.route('/ai_assistant')
def ai_assistant():
    """AI助手专业版页面 → 使用 Vue 应用"""
    return send_from_directory(
        os.path.join(BASE_DIR, 'templates', 'vue-dist'),
        'index.html',
        mimetype='text/html'
    )
```

### 修改 3: 添加 Vue 静态资源路由
在 `index()` 函数之后添加以下代码：

```python
@pages_bp.route('/assets/<path:path>')
def serve_vue_assets(path):
    """提供 Vue 构建的 assets 静态资源"""
    vue_dist_dir = os.path.join(BASE_DIR, 'templates', 'vue-dist')
    requested_path = os.path.join(vue_dist_dir, path)
    
    if os.path.exists(requested_path) and not os.path.isdir(requested_path):
        return send_from_directory(vue_dist_dir, path)
    
    vue_assets_dir = os.path.join(vue_dist_dir, 'assets')
    assets_path = os.path.join(vue_assets_dir, path)
    if os.path.exists(assets_path) and not os.path.isdir(assets_path):
        return send_from_directory(vue_assets_dir, path)
    
    return send_from_directory(vue_dist_dir, 'index.html')
```

## 步骤 5: 重启 Flask 应用

停止当前运行的 Flask 应用（如果正在运行），然后重新启动：

```bash
cd e:\FHD\AI助手
python app_api.py
```

## 步骤 6: 测试

打开浏览器访问：http://localhost:5000

您应该能看到 Vue 版本的 AI 智能助手控制台！

## 回滚方案

如果需要回滚到原 HTML 版本：

1. 将 `e:\FHD\AI助手\templates\ai_assistant_console.html.backup` 重命名回 `ai_assistant_console.html`
2. 恢复 `pages.py` 中的原始路由配置
3. 重启 Flask 应用

## 目录结构

完成部署后的目录结构：

```
e:\FHD\
├── AI助手\
│   ├── templates\
│   │   ├── vue-dist\              # Vue 构建产物
│   │   │   ├── index.html
│   │   │   └── assets\
│   │   ├── ai_assistant_console.html          # 原文件（已备份）
│   │   └── ai_assistant_console.html.backup   # 备份文件
│   └── routes\
│       └── pages.py              # 已修改的路由配置
└── ai-assistant-vue\
    ├── dist\                     # Vue 构建目录（源文件）
    └── ...
```

## 常见问题

### Q: 构建失败怎么办？
A: 请确保 Node.js 版本为 16.x 或更高，并删除 `node_modules` 文件夹和 `package-lock.json` 文件后重新运行 `npm install`。

### Q: 页面加载但显示空白？
A: 检查浏览器控制台（F12）是否有 404 错误，确保静态资源路径正确。

### Q: 如何切换回原版本？
A: 按照上面的"回滚方案"操作即可。
