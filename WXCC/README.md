# XCAGI 智能采购商城小程序

一个现代化的商城购物类微信小程序，采用清新的蓝色主题和流畅的交互体验。

## 项目特色

### 🎨 现代化 UI 设计
- 清新的蓝色主题 (#1890ff)
- 流畅的动画过渡效果
- 响应式布局，适配不同屏幕尺寸
- 卡片式设计，层次分明

### 🛍️ 完整商城功能
- **首页**: 轮播图、分类导航、公告栏、推荐商品
- **分类**: 左右联动分类浏览
- **商品详情**: 多图展示、规格选择、加入购物车
- **购物车**: 商品管理、数量调整、全选结算
- **订单**: 订单列表、订单详情、订单状态跟踪、物流跟踪、评价系统
- **个人中心**: 用户信息、地址管理、消息中心、商品收藏

### ✨ 新增功能
- **微信登录**: 支持手机号验证码登录和微信一键登录
- **微信支付**: 完整的支付流程，支持查询支付结果
- **物流跟踪**: 实时查看物流轨迹，支持复制运单号
- **商品收藏**: 本地和云端同步收藏列表
- **评价系统**: 支持评分、文字评价、上传图片
- **分享功能**: 商品分享、生成分享海报
- **骨架屏**: 加载时显示骨架屏，提升用户体验
- **图片懒加载**: 优化图片加载性能
- **虚拟列表**: 优化长列表性能
- **分包加载**: 优化小程序启动速度

### 📱 核心页面
#### 主包页面
- 首页 (`/pages/index/index`)
- 分类页 (`/pages/category/category`)
- 商品详情 (`/pages/product/detail/detail`)
- 购物车 (`/pages/cart/cart`)
- 搜索页 (`/pages/search/search`)
- 登录页 (`/pages/login/login`)
- 协议页 (`/pages/agreement/agreement`)

#### 订单分包
- 订单列表 (`/pages/order/list/list`)
- 订单详情 (`/pages/order/detail/detail`)
- 订单确认 (`/pages/order/confirm/confirm`)
- 订单结果 (`/pages/order/result/result`)
- 支付页 (`/pages/order/pay/pay`)
- 评价页 (`/pages/order/review/review`)
- 物流跟踪 (`/pages/order/logistics/logistics`)

#### 个人中心分包
- 个人中心 (`/pages/my/index/index`)
- 个人信息 (`/pages/my/info/info`)
- 商品收藏 (`/pages/my/favorite/favorite`)
- 地址列表 (`/pages/my/address/list/list`)
- 地址编辑 (`/pages/my/address/edit/edit`)

#### 其他页面
- 消息中心 (`/pages/message/list/list`)

### 🔧 技术特性
- 原生微信小程序开发
- Promise 封装的网络请求
- 本地存储管理购物车
- 防抖节流优化
- 下拉刷新和上拉加载
- 空状态和加载状态处理
- 骨架屏加载动画
- 图片懒加载
- 虚拟列表优化
- 分包加载优化
- 组件化开发

## 组件说明

### Skeleton 骨架屏组件
```xml
<skeleton isLoading="{{true}}" type="list" count="6"></skeleton>
```

### LazyImage 懒加载图片组件
```xml
<lazy-image src="{{imageUrl}}" placeholder="/assets/placeholder.png" />
```

### VirtualList 虚拟列表组件
```xml
<virtual-list items="{{list}}" itemHeight="160" height="600">
  <view slot="item" wx:for="{{item}}" wx:key="id">{{item.name}}</view>
</virtual-list>
```

## 快速开始

### 1. 配置小程序
编辑 `project.config.json`:
```json
{
  "appid": "你的小程序 AppID",
  "projectname": "xcagi-miniprogram"
}
```

### 2. 配置后端地址
编辑 `app.js`:
```javascript
globalData: {
  baseUrl: 'http://127.0.0.1:8000/api/mp/v1',  // 开发环境
  // baseUrl: 'https://your-domain.com/api/mp/v1',  // 生产环境
}
```

### 3. 导入微信开发者工具
1. 打开微信开发者工具
2. 导入项目，选择 `e:\FHD\WXCC` 目录
3. 编译运行

## 项目结构

```
WXCC/
├── app.js                 # 小程序入口
├── app.json              # 小程序配置
├── app.wxss              # 全局样式
├── project.config.json   # 项目配置
├── sitemap.json          # 搜索索引配置
├── utils/                # 工具类
│   ├── request.js        # 网络请求封装
│   └── util.js           # 通用工具函数
└── pages/                # 页面
    ├── index/            # 首页
    ├── category/         # 分类页
    ├── product/          # 商品相关
    │   └── detail/       # 商品详情
    ├── cart/             # 购物车
    ├── order/            # 订单相关
    │   ├── list/         # 订单列表
    │   ├── confirm/      # 订单确认
    │   ├── detail/       # 订单详情 (待实现)
    │   └── result/       # 订单结果
    ├── search/           # 搜索页
    ├── profile/          # 个人中心
    │   ├── index/        # 个人中心首页
    │   ├── info/         # 个人信息
    │   └── address/      # 地址管理
    │       ├── list/     # 地址列表
    │       └── edit/     # 地址编辑
    └── message/          # 消息中心
        └── list/         # 消息列表
```

## API 接口

### 产品相关
- `GET /products/list` - 获取产品列表
- `GET /products/:id` - 获取产品详情

### 订单相关
- `GET /orders` - 获取订单列表
- `POST /orders/create` - 创建订单
- `GET /orders/:id` - 获取订单详情

### 地址相关
- `GET /address/list` - 获取地址列表
- `POST /address/create` - 创建地址
- `PUT /address/:id` - 更新地址
- `DELETE /address/:id` - 删除地址

### 用户相关
- `GET /user/info` - 获取用户信息
- `PUT /user/profile` - 更新用户信息

## 开发说明

### 网络请求
```javascript
const { get, post } = require('../../utils/request')

// GET 请求
const res = await get('/products/list', { page: 1 })

// POST 请求
const res = await post('/orders/create', orderData)
```

### 工具函数
```javascript
const { formatPrice, formatDate, validatePhone } = require('../../utils/util')

// 格式化价格
const price = formatPrice(299)  // ¥299.00

// 格式化日期
const date = formatDate(new Date())  // 2024-01-01

// 验证手机号
const valid = validatePhone('13800138000')  // true
```

## 待完善功能

- [ ] 微信登录对接
- [ ] 支付功能
- [ ] 物流跟踪
- [ ] 商品收藏
- [ ] 优惠券系统
- [ ] 评价系统
- [ ] 客服聊天
- [ ] 分享功能

## 技术栈

- 微信小程序原生开发
- ES6+
- Promise 异步处理
- 本地存储 (wx.Storage)

## 注意事项

1. 首次使用需要在微信公众平台注册小程序账号
2. 开发阶段可以使用测试账号
3. 生产环境需要配置合法的域名
4. 部分功能需要后端 API 支持

## 开发者

基于 XCAGI 后端系统开发

## License

MIT
