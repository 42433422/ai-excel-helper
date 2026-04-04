# XCAGI 微信小程序系统 - 完整规格说明书

## 1. 项目概述

### 1.1 项目名称
**XCAGI CRM Mini Program (XCAGI-CRM-MP)**

### 1.2 项目定位
基于现有 XCAGI 企业管理系统的微信小程序端，为客户提供移动端 CRM 服务，实现客户自主下单、订单跟踪、库存查询、在线客服等核心功能。

### 1.3 目标用户
- **B2B 客户**: 涂料/化工行业的企业客户
- **销售代表**: 通过小程序辅助客户下单
- **管理员**: 管理后台数据同步

---

## 2. 技术架构对比分析

### 2.1 传统 CRM vs XCAGI 小程序 CRM 对比

| 维度 | 传统 CRM 系统 | XCAGI 小程序 CRM |
|------|-------------|-----------------|
| **访问方式** | PC Web / 安装客户端 | 微信小程序（无需安装） |
| **用户门槛** | 需要账号密码注册 | 微信一键授权登录 |
| **部署成本** | 高（服务器+客户端维护） | 低（云端部署） |
| **数据同步** | 需手动/定时同步 | 实时双向同步 |
| **AI 能力** | 基础规则引擎 | DeepSeek + BERT AI 对话 |
| **行业适配** | 通用型 | 涂料/化工行业深度定制 |
| **微信集成** | 无/弱集成 | 深度集成（联系人、消息） |
| **离线能力** | 无 | 支持基础离线操作 |
| **推送通知** | 邮件/短信 | 微信模板消息/订阅消息 |

### 2.2 同类小程序对比

| 功能模块 | 有赞零售 | 微盟智慧零售 | **XCAGI 小程序** |
|---------|---------|-------------|-----------------|
| 商品展示 | ✅ | ✅ | ✅ |
| 在线下单 | ✅ | ✅ | ✅ |
| 订单管理 | ✅ | ✅ | ✅ |
| 库存查询 | ❌ | ⚠️ 有限 | ✅ 实时 |
| AI 智能客服 | ⚠️ 规则匹配 | ⚠️ 关键词 | ✅ DeepSeek 大模型 |
| 价格计算 | 标准价 | 标准价 | ✅ 行业定价引擎 |
| 发货跟踪 | 物流对接 | 物流对接 | ✅ 自建物流+标签打印 |
| 数据分析 | ✅ | ✅ | ✅ Kitten Report |
| 行业定制 | 通用 | 通用 | ✅ 涂料/化工专属 |
| 私有部署 | ❌ SaaS | ❌ SaaS | ✅ 支持 |

### 2.3 XCAGI 核心竞争优势

1. **AI 驱动**: DeepSeek 大模型 + BERT 意图识别，支持自然语言下单
2. **行业深度**: 针对涂料/化工行业的定价引擎、配方管理
3. **全链路闭环**: 从询价→下单→生产→发货→售后完整流程
4. **私有化部署**: 数据完全自控，适合 B2B 场景
5. **微信生态整合**: 联系人同步、消息解析、自动化任务

---

## 3. 系统技术栈

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     微信小程序前端                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │ 首页/商品 │ │ 购物车   │ │ 订单中心 │ │ 个人中心 │       │
│  └─────┬────┘ └─────┬────┘ └─────┬────┘ └─────┬────┘       │
│        └────────────┴────────────┴────────────┘              │
│                         ↓ HTTPS                              │
├─────────────────────────────────────────────────────────────┤
│                    API Gateway (Nginx)                       │
├─────────────────────────────────────────────────────────────┤
│                   Flask 后端服务                             │
│  ┌──────────────────────────────────────────────────┐       │
│  │  小程序 API 层 (app/routes/miniprogram_*.py)      │       │
│  ├──────────────────────────────────────────────────┤       │
│  │  业务逻辑层 (app/application/)                    │       │
│  ├──────────────────────────────────────────────────┤       │
│  │  领域模型层 (app/domain/)                        │       │
│  ├──────────────────────────────────────────────────┤       │
│  │  基础设施层 (app/infrastructure/)                │       │
│  └──────────────────────────────────────────────────┘       │
├─────────────────────────────────────────────────────────────┤
│                      数据层                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ PostgreSQL   │  │ Redis        │  │ MinIO/OSS    │      │
│  │ (主数据库)    │  │ (缓存/会话)   │  │ (文件存储)    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 前端技术栈（小程序）

| 技术 | 版本/说明 |
|-----|---------|
| 框架 | 微信小程序原生框架 (WXML/WXSS/JS) |
| UI 组件库 | Vant Weapp 2.x / 自定义组件 |
| 状态管理 | 全局 app.js + 页面 data |
| 网络请求 | wx.request 封装 |
| 支付 | wx.requestPayment |
| 地图 | wx.getLocation / wx.chooseLocation |
| 扫码 | wx.scanCode |

### 3.3 后端技术栈（扩展现有）

| 技术 | 说明 |
|-----|------|
| 框架 | Flask 3.0 (已有) |
| ORM | SQLAlchemy 2.0 (已有) |
| 数据库 | PostgreSQL + pgvector (已有) |
| 缓存 | Redis (已有) |
| 任务队列 | Celery (已有) |
| AI 引擎 | DeepSeek + BERT (已有) |
| 认证 | JWT (已实现 wechat_miniprogram.py) |

### 3.4 数据库设计

#### 3.4.1 核心表结构（新增/扩展）

```sql
-- 小程序用户表（扩展 User 表）
ALTER TABLE users ADD COLUMN IF NOT EXISTS wx_openid VARCHAR(64) UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS wx_unionid VARCHAR(64);
ALTER TABLE users ADD COLUMN IF NOT EXISTS wx_avatar_url TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS mp_phone VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS mp_nickname VARCHAR(64);

-- 小程序购物车表
CREATE TABLE mp_carts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL DEFAULT 1,
    selected BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, product_id)
);

-- 小程序订单表（扩展或新建）
CREATE TABLE mp_orders (
    id SERIAL PRIMARY KEY,
    order_no VARCHAR(32) NOT NULL UNIQUE,
    user_id INTEGER NOT NULL REFERENCES users(id),
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    total_amount DECIMAL(12,2) NOT NULL,
    pay_amount DECIMAL(12,2),
    pay_status VARCHAR(20) DEFAULT 'unpaid',
    pay_time TIMESTAMP,
    delivery_name VARCHAR(64),
    delivery_phone VARCHAR(20),
    delivery_address TEXT,
    delivery_province VARCHAR(32),
    delivery_city VARCHAR(32),
    delivery_district VARCHAR(32),
    remark TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 小程序订单明细表
CREATE TABLE mp_order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES mp_orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    product_name VARCHAR(128) NOT NULL,
    product_sku VARCHAR(64),
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(10,2) NOT NULL,
    subtotal DECIMAL(12,2) NOT NULL,
    remark TEXT
);

-- 小程序收货地址表
CREATE TABLE mp_addresses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    contact_name VARCHAR(32) NOT NULL,
    contact_phone VARCHAR(20) NOT NULL,
    province VARCHAR(32) NOT NULL,
    city VARCHAR(32) NOT NULL,
    district VARCHAR(32) NOT NULL,
    detail_address TEXT NOT NULL,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 浏览记录表
CREATE TABLE mp_browse_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, product_id)
);

-- 收藏表
CREATE TABLE mp_favorites (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, product_id)
);

-- 消息通知表
CREATE TABLE mp_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title VARCHAR(128) NOT NULL,
    content TEXT,
    type VARCHAR(32) DEFAULT 'system',
    is_read BOOLEAN DEFAULT false,
    related_type VARCHAR(32),
    related_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 小程序反馈表
CREATE TABLE mp_feedback (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    type VARCHAR(32) NOT NULL,
    content TEXT NOT NULL,
    images JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    reply TEXT,
    replied_by INTEGER,
    replied_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. API 接口设计

### 4.1 接口规范

- **Base URL**: `/api/mp/v1`
- **认证方式**: Bearer Token (JWT)
- **响应格式**: 统一 JSON 格式
- **编码**: UTF-8

#### 统一响应格式

```json
{
    "code": 200,
    "message": "success",
    "success": true,
    "data": {}
}
```

### 4.2 API 接口清单

#### 4.2.1 用户模块 (`/api/mp/v1/user`)

| 方法 | 路径 | 描述 | 认证 |
|-----|------|------|-----|
| POST | /wechat/login | 微信登录 | 否 |
| GET | /info | 获取用户信息 | 是 |
| PUT | /info | 更新用户信息 | 是 |
| GET | /phone | 获取手机号 | 是 |

#### 4.2.2 首页模块 (`/api/mp/v1/home`)

| 方法 | 路径 | 描述 | 认证 |
|-----|------|------|-----|
| GET | /banner | 获取轮播图 | 否 |
| GET | /recommend | 推荐商品 | 否 |
| GET | /notice | 公告列表 | 否 |
| GET | /stats | 用户统计概览 | 是 |

#### 4.2.3 商品模块 (`/api/mp/v1/product`)

| 方法 | 路径 | 描述 | 认证 |
|-----|------|------|-----|
| GET | /list | 商品列表（分页/搜索/筛选） | 否 |
| GET | /detail/:id | 商品详情 | 否 |
| GET | /categories | 分类列表 | 否 |
| GET | /search | 搜索商品（支持AI搜索） | 否 |
| GET | /price/:id | 获取实时价格 | 是 |
| POST | /inquiry | 询价 | 是 |

#### 4.2.4 购物车模块 (`/api/mp/v1/cart`)

| 方法 | 路径 | 描述 | 认证 |
|-----|------|------|-----|
| GET | /list | 购物车列表 | 是 |
| POST | /add | 添加到购物车 | 是 |
| PUT | /update | 更新数量 | 是 |
| DELETE | /remove | 删除商品 | 是 |
| PUT | /select | 选择/取消选择 | 是 |
| DELETE | /clear | 清空购物车 | 是 |

#### 4.2.5 订单模块 (`/api/mp/v1/order`)

| 方法 | 路径 | 描述 | 认证 |
|-----|------|------|-----|
| POST | /create | 创建订单 | 是 |
| GET | /list | 订单列表 | 是 |
| GET | /detail/:id | 订单详情 | 是 |
| PUT | /cancel | 取消订单 | 是 |
| POST | /pay | 发起支付 | 是 |
| GET | /status/:id | 支付状态查询 | 是 |
| PUT | /confirm | 确认收货 | 是 |
| POST | /rebuy | 再次购买 | 是 |

#### 4.2.6 地址模块 (`/api/mp/v1/address`)

| 方法 | 路径 | 描述 | 认证 |
|-----|------|------|-----|
| GET | /list | 地址列表 | 是 |
| POST | /create | 新增地址 | 是 |
| PUT | /update/:id | 更新地址 | 是 |
| DELETE | /delete/:id | 删除地址 | 是 |
| PUT | /default/:id | 设为默认 | 是 |

#### 4.2.7 收藏模块 (`/api/mp/v1/favorite`)

| 方法 | 路径 | 描述 | 认证 |
|-----|------|------|-----|
| GET | /list | 收藏列表 | 是 |
| POST | /add | 添加收藏 | 是 |
| DELETE | /remove/:id | 取消收藏 | 是 |
| GET | /check/:id | 是否收藏 | 是 |

#### 4.2.8 消息模块 (`/api/mp/v1/message`)

| 方法 | 路径 | 描述 | 认证 |
|-----|------|------|-----|
| GET | /list | 消息列表 | 是 |
| PUT | /read/:id | 标记已读 | 是 |
| PUT | /read-all | 全部已读 | 是 |
| GET | /unread-count | 未读数 | 是 |

#### 4.2.9 AI 客服模块 (`/api/mp/v1/ai`)

| 方法 | 路径 | 描述 | 认证 |
|-----|------|------|-----|
| POST | /chat | AI 对话 | 是 |
| GET | /history | 对话历史 | 是 |
| POST | /voice | 语音转文字+回复 | 是 |
| GET | /intents | 常用意图列表 | 否 |

#### 4.2.10 反馈模块 (`/api/mp/v1/feedback`)

| 方法 | 路径 | 描述 | 认证 |
|-----|------|------|-----|
| POST | /submit | 提交反馈 | 是 |
| GET | /list | 我的反馈 | 是 |
| GET | /detail/:id | 反馈详情 | 是 |

---

## 5. 小程序页面结构

### 5.1 页面路由配置

```
pages/
├── index/                  # 首页
│   ├── index.wxml
│   ├── index.wxss
│   ├── index.js
│   └── index.json
├── category/               # 分类页
│   ├── category.wxml
│   ├── category.wxss
│   ├── category.js
│   └── category.json
├── product/                # 商品详情
│   ├── detail.wxml
│   ├── detail.wxss
│   ├── detail.js
│   └── detail.json
├── search/                 # 搜索页
│   ├── search.wxml
│   ├── search.wxss
│   ├── search.js
│   └── search.json
├── cart/                   # 购物车
│   ├── cart.wxml
│   ├── cart.wxss
│   ├── cart.js
│   └── cart.json
├── order/                  # 订单相关
│   ├── confirm/            # 确认订单
│   ├── list/               # 订单列表
│   ├── detail/             # 订单详情
│   └── result/             # 支付结果
├── address/                # 地址管理
│   ├── list/
│   ├── edit/
│   └── select/
├── profile/                # 个人中心
│   ├── index/
│   ├── info/
│   ├── favorite/
│   ├── browse-history/
│   ├── feedback/
│   └── settings/
├── chat/                   # AI 客服
│   ├── chat.wxml
│   ├── chat.wxss
│   ├── chat.js
│   └── chat.json
└── notice/                 # 消息中心
    ├── list/
    └── detail/
```

### 5.2 TabBar 配置

```json
{
    "tabBar": {
        "color": "#999999",
        "selectedColor": "#1890ff",
        "backgroundColor": "#ffffff",
        "borderStyle": "black",
        "list": [
            {
                "pagePath": "pages/index/index",
                "text": "首页",
                "iconPath": "assets/tab/home.png",
                "selectedIconPath": "assets/tab/home-active.png"
            },
            {
                "pagePath": "pages/category/category",
                "text": "分类",
                "iconPath": "assets/tab/category.png",
                "selectedIconPath": "assets/tab/category-active.png"
            },
            {
                "pagePath": "pages/cart/cart",
                "text": "购物车",
                "iconPath": "assets/tab/cart.png",
                "selectedIconPath": "assets/tab/cart-active.png"
            },
            {
                "pagePath": "pages/profile/index",
                "text": "我的",
                "iconPath": "assets/tab/profile.png",
                "selectedIconPath": "assets/tab/profile-active.png"
            }
        ]
    }
}
```

---

## 6. 核心功能详细说明

### 6.1 用户认证流程

```
[小程序启动] → [检查本地token] → [有效?]
                                    ↓ 是                              ↓ 否
                            [直接使用]                    [wx.login() 获取 code]
                                                                ↓
                                                    [发送 code 到后端]
                                                                ↓
                                                    [后端调用微信 code2Session]
                                                                ↓
                                                    [获取 openid, session_key]
                                                                ↓
                                                    [查找/创建用户]
                                                                ↓
                                                    [生成 JWT Token]
                                                                ↓
                                                    [返回 token 给小程序]
                                                                ↓
                                                    [本地存储 token]
```

### 6.2 下单流程

```
[浏览商品] → [加入购物车] → [去结算]
                                ↓
                    [选择/添加收货地址]
                                ↓
                    [确认商品信息+价格]
                                ↓
                    [填写备注(可选)]
                                ↓
                    [提交订单]
                                ↓
                    [生成订单号]
                                ↓
                    [调用微信支付]
                                ↓
                [支付成功/失败回调]
                        ↓           ↓
                [更新订单状态]   [提示重试]
```

### 6.3 AI 智能客服

基于现有的 DeepSeek + BERT 架构：

- **意图识别**: BERT 模型识别用户意图（询价、下单、查物流等）
- **对话生成**: DeepSeek 大模型生成自然语言回复
- **上下文管理**: 维护会话上下文，支持多轮对话
- **知识库检索**: 结合产品库、价格库实时回答

### 6.4 与现有系统集成点

| 集成项 | 现有模块 | 小程序接口 |
|-------|---------|-----------|
| 产品数据 | `products` 表 | `/api/mp/v1/product/*` |
| 价格计算 | `pricing_engine.py` | `/api/mp/v1/product/price/:id` |
| 客户信息 | `customers` 表 | `/api/mp/v1/user/info` |
| 出货系统 | `shipment` 模块 | `/api/mp/v1/order/*` |
| AI 对话 | `ai_chat` 服务 | `/api/mp/v1/ai/chat` |
| 微信联系人 | `wechat_contact` 服务 | 用户绑定 |

---

## 7. 安全设计

### 7.1 认证安全

- JWT Token 有效期 30 天
- Token 刷新机制
- 敏感操作二次验证

### 7.2 数据安全

- HTTPS 强制加密
- 用户数据隔离（租户模式）
- 敏感字段加密存储
- SQL 注入防护（ORM 参数化）

### 7.3 接口安全

- 请求频率限制（Rate Limiting）
- 签名校验（防篡改）
- XSS 防护
- CSRF 防护

---

## 8. 性能要求

| 指标 | 要求 |
|-----|------|
| API 响应时间 | P99 < 500ms |
| 并发用户数 | 支持 1000+ 同时在线 |
| 页面加载 | 首屏 < 2秒 |
| 离线缓存 | 支持基础功能离线 |

---

## 9. 部署方案

### 9.1 开发环境

```
本地开发 → 微信开发者工具 → 连接本地后端
```

### 9.2 生产环境

```
小程序发布 → 微信审核 → 上线
后端: Docker + Nginx + Gunicorn
数据库: PostgreSQL (主从)
缓存: Redis Cluster
```

---

## 10. 项目目录结构（目标）

```
e:\FHD\XCAGI\
├── miniprogram/                    # 【新增】小程序前端代码
│   ├── pages/                      # 页面目录
│   ├── components/                 # 自定义组件
│   ├── utils/                      # 工具函数
│   ├── api/                        # API 封装
│   ├── assets/                     # 静态资源
│   ├── styles/                     # 全局样式
│   ├── app.js                      # 小程序入口
│   ├── app.json                    # 全局配置
│   ├── app.wxss                    # 全局样式
│   └── project.config.json         # 项目配置
│
├── app/
│   ├── routes/
│   │   ├── mp_auth.py             # 【新增】小程序认证
│   │   ├── mp_user.py             # 【新增】用户模块
│   │   ├── mp_product.py          # 【新增】商品模块
│   │   ├── mp_cart.py             # 【新增】购物车模块
│   │   ├── mp_order.py            # 【新增】订单模块
│   │   ├── mp_address.py          # 【新增】地址模块
│   │   ├── mp_favorite.py         # 【新增】收藏模块
│   │   ├── mp_message.py          # 【新增】消息模块
│   │   ├── mp_ai.py               # 【新增】AI客服
│   │   └── mp_feedback.py         # 【新增】反馈模块
│   ├── db/models/
│   │   └── miniprogram.py         # 【新增】小程序数据模型
│   ├── schemas/
│   │   └── mp_schema.py           # 【新增】小程序请求/响应Schema
│   └── services/
│       ├── mp_cart_service.py     # 【新增】购物车服务
│       ├── mp_order_service.py    # 【新增】订单服务
│       └── mp_notification_service.py # 【新增】通知服务
│
├── alembic/versions/
│   └── xxx_add_miniprogram_tables.py  # 【新增】数据库迁移
│
└── resources/config/
    └── miniprogram.yaml           # 【新增】小程序配置
```
