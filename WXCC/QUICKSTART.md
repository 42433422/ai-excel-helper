# 快速启动指南

## ✅ 当前状态

小程序已可以编译运行，但需要完善以下内容：

## 🚀 立即可以做的

### 方案一：使用 Mock 数据（推荐用于开发）

修改配置使用本地 Mock 数据，不依赖后端：

1. **修改 `utils/request.js`**
   启用 Mock 模式

2. **优势**
   - 无需启动后端
   - 开发更快速
   - 测试更方便

### 方案二：启动后端服务

1. **启动 FastAPI 后端**
   ```bash
   cd e:\FHD\XCAGI
   # 激活虚拟环境
   .venv\Scripts\activate  # Windows
   # 或 source .venv/bin/activate  # Linux/Mac
   
   # 启动服务
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **验证 API**
   访问：http://127.0.0.1:8000/api/mp/v1/products/list

### 方案三：使用网络占位图

修改页面使用在线占位图，避免图片错误。

## 📝 详细配置

### 1. 启用 Mock 模式

编辑 `utils/request.js`，添加 Mock 数据：

```javascript
// 在文件顶部添加
const USE_MOCK = true // 设置为 true 启用 Mock

// 修改 request 函数
if (USE_MOCK) {
  return mockRequest(url, method, data)
}
```

### 2. 添加占位图片

创建简单的纯色图片作为占位符。

#### 方法 A：使用在线服务
修改 WXML 使用网络图片：

```xml
<image src="https://via.placeholder.com/750x400?text=Banner" />
```

#### 方法 B：创建本地 SVG
微信小程序支持 SVG：

```xml
<!-- 创建简单的 SVG 占位图 -->
<view class="placeholder" style="background-color: #f0f0f0; height: 400rpx;"></view>
```

### 3. 更新废弃 API

编辑 `app.js` 第 39 行：

```javascript
// 旧代码
const systemInfo = wx.getSystemInfoSync()

// 新代码
const systemInfo = wx.getSystemInfo()
```

## 🎯 推荐步骤

### 开发阶段
1. ✅ 启用 Mock 数据
2. ✅ 使用占位图片
3. ✅ 专注功能开发

### 测试阶段
1. ✅ 接入真实 API
2. ✅ 添加真实图片
3. ✅ 性能优化

### 上线阶段
1. ✅ 完整测试
2. ✅ 资源优化
3. ✅ 提交审核

## 📦 快速测试

### 1. 清除缓存
工具 → 清除缓存 → 清除全部缓存

### 2. 重新编译
点击编译按钮

### 3. 查看效果
忽略图片错误，测试功能流程

## 🛠️ 下一步完善

### 优先级 1 - 功能完善
- [ ] 实现 Mock 数据
- [ ] 完善登录流程
- [ ] 测试订单流程

### 优先级 2 - 资源完善
- [ ] 添加 TabBar 图标
- [ ] 添加分类图标
- [ ] 添加商品图片
- [ ] 添加轮播图

### 优先级 3 - 后端对接
- [ ] 启动后端服务
- [ ] 配置 API 地址
- [ ] 测试接口连通性

## 📞 获取帮助

参考文档：
- [`README.md`](file:///e:/FHD/WXCC/README.md) - 项目说明
- [`GUIDE.md`](file:///e:/FHD/WXCC/GUIDE.md) - 使用指南
- [`FIXES.md`](file:///e:/FHD/WXCC/FIXES.md) - 问题修复
- [`assets/PLACEHOLDER_GUIDE.md`](file:///e:/FHD/WXCC/assets/PLACEHOLDER_GUIDE.md) - 占位图指南
