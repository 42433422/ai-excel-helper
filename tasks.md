# XCAGI 微信小程序系统 - 任务分解清单

## 阶段一：基础架构搭建 (Phase 1: Foundation)

### 1.1 数据库层
- [ ] **T1.1.1** 创建小程序数据库模型文件 `app/db/models/miniprogram.py`
  - 定义 MpCart, MpOrder, MpOrderItem, MpAddress, MpBrowseHistory, MpFavorite, MpNotification, MpFeedback 模型
  - 扩展 User 表添加微信相关字段（wx_openid, wx_unionid 等）
- [ ] **T1.1.2** 创建 Alembic 迁移文件 `alembic/versions/xxx_add_miniprogram_tables.py`
  - 执行所有新增表的 DDL
  - 添加必要的索引（user_id, order_no 等）
- [ ] **T1.1.3** 编写数据库初始化脚本 `app/db/init_mp_db.py`
  - 创建默认数据（如公告、分类等）

### 1.2 后端 API 基础
- [ ] **T1.2.1** 创建小程序 API 蓝图注册 `app/routes/__init__.py` 更新
  - 注册所有小程序 API 蓝图，前缀 `/api/mp/v1`
- [ ] **T1.2.2** 创建统一响应工具 `app/utils/mp_response.py`
  - 封装 success(), error(), paginate() 等方法
- [ ] **T1.2.3** 创建请求验证装饰器 `app/decorators/mp_auth.py`
  - 基于 JWT 的认证装饰器
  - 频率限制装饰器

---

## 阶段二：用户认证模块 (Phase 2: Authentication)

### 2.1 微信登录
- [ ] **T2.1.1** 实现微信登录接口 `app/routes/mp_auth.py`
  - POST `/api/mp/v1/wechat/login` 接收 code
  - 调用微信 code2Session API
  - 创建/查找用户，返回 JWT Token
- [ ] **T2.1.2** 实现 Token 刷新机制
  - 刷新接口设计
  - 双 Token 方案（Access + Refresh）

### 2.2 用户信息管理
- [ ] **T2.2.1** 实现用户信息接口 `app/routes/mp_user.py`
  - GET `/api/mp/v1/user/info` 获取当前用户
  - PUT `/api/mp/v1/user/info` 更新昵称/头像
  - GET `/api/mp/v1/user/phone` 获取手机号（微信 getPhoneNumber）
- [ ] **T2.2.2** 创建 Schema 定义 `app/schemas/mp_schema.py`
  - UserSchema, UserUpdateSchema
  - 请求参数校验

### 2.3 会话管理
- [ ] **T2.3.1** 实现会话检查接口
  - GET `/api/mp/v1/session/check`
  - Token 有效性验证
- [ ] **T2.3.2** 实现登出接口
  - POST `/api/mp/v1/user/logout`

---

## 阶段三：商品模块 (Phase 3: Product)

### 3.1 商品展示
- [ ] **T3.1.1** 实现商品列表接口 `app/routes/mp_product.py`
  - GET `/api/mp/v1/product/list`
  - 支持分页、搜索、分类筛选、排序
  - 复用现有 Product 模型
- [ ] **T3.1.2** 实现商品详情接口
  - GET `/api/mp/v1/product/detail/:id`
  - 返回完整商品信息（规格、图片、库存等）
- [ ] **T3.1.3** 实现分类接口
  - GET `/api/mp/v1/product/categories`
  - 返回分类树结构

### 3.2 商品搜索
- [ ] **T3.2.1** 实现搜索接口
  - GET `/api/mp/v1/product/search`
  - 支持关键词搜索
  - 可选：集成 AI 语义搜索（复用 pgvector）
- [ ] **T3.2.2** 实现价格查询接口
  - GET `/api/mp/v1/product/price/:id`
  - 调用现有 pricing_engine 计算实时价格

### 3.3 询价功能
- [ ] **T3.3.1** 实现询价接口
  - POST `/api/mp/v1/product/inquiry`
  - 创建询价记录，通知销售

---

## 阶段四：购物车模块 (Phase 4: Cart)

### 4.1 购物车 CRUD
- [ ] **T4.1.1** 实现购物车服务 `app/services/mp_cart_service.py`
  - add_item(): 添加商品
  - update_quantity(): 更新数量
  - remove_item(): 删除商品
  - clear_cart(): 清空购物车
  - select_item(): 选择/取消选择
- [ ] **T4.2.1** 实现购物车 API `app/routes/mp_cart.py`
  - GET `/api/mp/v1/cart/list` 获取购物车列表（含选中状态、小计）
  - POST `/api/mp/v1/cart/add` 添加到购物车
  - PUT `/api/mp/v1/cart/update` 更新数量
  - DELETE `/api/mp/v1/cart/remove` 删除商品
  - PUT `/api/mp/v1/cart/select` 选择/取消
  - DELETE `/api/mp/v1/cart/clear` 清空

---

## 阶段五：订单模块 (Phase 5: Order)

### 5.1 订单创建流程
- [ ] **T5.1.1** 实现订单服务 `app/services/mp_order_service.py`
  - create_order(): 创建订单（从购物车生成）
  - calculate_total(): 计算总价
  - generate_order_no(): 生成唯一订单号
  - validate_inventory(): 校验库存
- [ ] **T5.1.2** 实现创建订单接口
  - POST `/api/mp/v1/order/create`
  - 参数：address_id, cart_items[], remark
  - 返回：order_id, pay_params

### 5.2 订单查询与管理
- [ ] **T5.2.1** 实现订单列表接口
  - GET `/api/mp/v1/order/list`
  - 支持按状态筛选（全部/待付款/待发货/已完成）
- [ ] **T5.2.2** 实现订单详情接口
  - GET `/api/mp/v1/order/detail/:id`
  - 返回完整订单信息含物流信息
- [ ] **T5.2.3** 实现取消订单接口
  - PUT `/api/mp/v1/order/cancel/:id`

### 5.3 支付集成
- [ ] **T5.3.1** 实现微信支付接口
  - POST `/api/mp/v1/order/pay/:id`
  - 调用微信支付统一下单 API
  - 返回支付参数给小程序
- [ ] **T5.3.2** 实现支付回调处理
  - POST `/api/mp/v1/pay/callback`
  - 验证签名，更新订单状态
- [ ] **T5.3.3** 实现支付状态查询
  - GET `/api/mp/v1/order/status/:id`

### 5.4 订单完成
- [ ] **T5.4.1** 实现确认收货接口
  - PUT `/api/mp/v1/order/confirm/:id`
- [ ] **T5.4.2** 实现再次购买接口
  - POST `/api/mp/v1/order/rebuy/:id`

---

## 阶段六：地址管理模块 (Phase 6: Address)

### 6.1 地址 CRUD
- [ ] **T6.1.1** 实现地址 API `app/routes/mp_address.py`
  - GET `/api/mp/v1/address/list` 地址列表
  - POST `/api/mp/v1/address/create` 新增地址
  - PUT `/api/mp/v1/address/update/:id` 更新地址
  - DELETE `/api/mp/v1/address/delete/:id` 删除地址
  - PUT `/api/mp/v1/address/default/:id` 设为默认

---

## 阶段七：收藏与浏览记录 (Phase 7: Favorite & History)

### 7.1 收藏功能
- [ ] **T7.1.1** 实现收藏 API `app/routes/mp_favorite.py`
  - GET `/api/mp/v1/favorite/list` 收藏列表
  - POST `/api/mp/v1/favorite/add` 添加收藏
  - DELETE `/api/mp/v1/favorite/remove/:id` 取消收藏
  - GET `/api/mp/v1/favorite/check/:id` 检查是否收藏

### 7.2 浏览记录
- [ ] **T7.2.1** 实现浏览记录自动记录
  - 在商品详情接口中自动记录
  - 支持批量记录优化性能
- [ ] **T7.2.2** 实现浏览历史查询
  - GET `/api/mp/v1/user/browse-history`

---

## 阶段八：消息通知模块 (Phase 8: Message)

### 8.1 消息中心
- [ ] **T8.1.1** 实现消息 API `app/routes/mp_message.py`
  - GET `/api/mp/v1/message/list` 消息列表（分页）
  - PUT `/api/mp/v1/message/read/:id` 标记已读
  - PUT `/api/mp/v1/message/read-all` 全部已读
  - GET `/api/mp/v1/message/unread-count` 未读数

### 8.2 消息推送
- [ ] **T8.2.1** 实现订阅消息发送服务
  - 订单状态变更通知
  - 发货通知
  - 支付成功通知

---

## 阶段九：AI 智能客服模块 (Phase 9: AI Chat)

### 9.1 AI 对话
- [ ] **T9.1.1** 实现小程序 AI 对话接口 `app/routes/mp_ai.py`
  - POST `/api/mp/v1/ai/chat` 发送消息
  - 复用现有 DeepSeek + BERT 架构
  - 支持流式响应
- [ ] **T9.1.2** 实现对话历史
  - GET `/api/mp/v1/ai/history` 获取历史对话

### 9.2 语音交互
- [ ] **T9.2.1** 实现语音输入接口
  - POST `/api/mp/v1/ai/voice`
  - 语音转文字 → AI 回复 → 文字转语音（可选）

---

## 阶段十：反馈模块 (Phase 10: Feedback)

### 10.1 用户反馈
- [ ] **T10.1.1** 实现反馈 API `app/routes/mp_feedback.py`
  - POST `/api/mp/v1/feedback/submit` 提交反馈（支持图片）
  - GET `/api/mp/v1/feedback/list` 我的反馈列表
  - GET `/api/mp/v1/feedback/detail/:id` 反馈详情

---

## 阶段十一：小程序前端开发 (Phase 11: Frontend)

### 11.1 项目初始化
- [ ] **T11.1.1** 创建小程序项目结构 `miniprogram/`
  - app.js, app.json, app.wxss, project.config.json
  - 配置 TabBar、页面路由
- [ ] **T11.1.2** 创建全局样式和主题变量
  - 定义颜色规范、字体、间距
  - 响应式适配（rpx 单位）

### 11.2 公共组件
- [ ] **T11.2.1** 开发基础组件 `miniprogram/components/`
  - custom-navbar: 自定义导航栏
  - product-card: 商品卡片
  - empty-state: 空状态组件
  - loading: 加载组件
  - price-display: 价格显示组件
  - image-uploader: 图片上传组件

### 11.3 工具函数
- [ ] **T11.3.1** 封装网络请求 `miniprogram/api/request.js`
  - 统一请求封装（Token 注入、错误处理、重试）
  - 拦截器（401 自动跳转登录）
- [ ] **T11.3.2** 封装各模块 API `miniprogram/api/modules/`
  - user.js, product.js, cart.js, order.js, address.js 等

### 11.4 页面开发
- [ ] **T11.4.1** 首页 `pages/index/`
  - 轮播 Banner
  - 分类入口
  - 推荐商品列表
  - 搜索框
- [ ] **T11.4.2** 分类页 `pages/category/`
  - 左侧分类树
  - 右侧商品列表
- [ ] **T11.4.3** 商品详情页 `pages/product/detail/`
  - 商品图片轮播
  - 价格、规格信息
  - 加入购物车/立即购买按钮
  - 商品介绍
- [ ] **T11.4.4** 搜索页 `pages/search/`
  - 搜索框
  - 搜索历史
  - 热门搜索
  - 搜索结果列表
- [ ] **T11.4.5** 购物车页 `pages/cart/`
  - 商品列表（可编辑数量、选择）
  - 全选/反选
  - 价格汇总
  - 去结算按钮
- [ ] **T11.4.6** 订单确认页 `pages/order/confirm/`
  - 收货地址选择
  - 商品清单
  - 价格明细
  - 提交订单
- [ ] **T11.4.7** 订单列表页 `pages/order/list/`
  - Tab 切换（全部/待付款/待发货/待收货/已完成）
  - 订单卡片
  - 下拉刷新/上拉加载更多
- [ ] **T11.4.8** 订单详情页 `pages/order/detail/`
  - 订单状态时间轴
  - 商品信息
  - 物流信息
  - 操作按钮（取消/确认收货/再次购买）
- [ ] **T11.4.9** 支付结果页 `pages/order/result/`
  - 支付成功/失败状态展示
  - 订单信息摘要
- [ ] **T11.4.10** 地址管理页 `pages/address/`
  - 地址列表
  - 新增/编辑地址表单
  - 地图选点
- [ ] **T11.4.11** 个人中心 `pages/profile/index/`
  - 用户头像/昵称
  - 订单快捷入口
  - 功能菜单（收藏、浏览历史、设置等）
- [ ] **T11.4.12** 个人信息编辑页 `pages/profile/info/`
  - 修改昵称
  - 修改头像
- [ ] **T11.4.13** 收藏页 `pages/profile/favorite/`
  - 收藏商品列表
  - 取消收藏
- [ ] **T11.4.14** 浏览历史页 `pages/profile/browse-history/`
  - 浏览记录列表
  - 清空历史
- [ ] **T11.4.15** 消息中心 `pages/message/`
  - 消息列表
  - 消息详情
- [ ] **T11.4.16** AI 客服页 `pages/chat/`
  - 对话界面
  - 输入框
  - 快捷问题
  - 语音输入按钮
- [ ] **T11.4.17** 反馈页 `pages/profile/feedback/`
  - 反馈表单
  - 图片上传
  - 反馈记录列表

---

## 阶段十二：集成测试与部署 (Phase 12: Testing & Deployment)

### 12.1 测试
- [ ] **T12.1.1** 编写后端单元测试
  - 各 API 接口测试
  - 业务逻辑测试
- [ ] **T12.1.2** 小程序真机调试
  - 微信开发者工具调试
  - 真机预览测试
- [ ] **T12.1.3** 联调测试
  - 前后端联调
  - 支付流程联调
  - 消息推送测试

### 12.2 部署配置
- [ ] **T12.2.1** 更新 Nginx 配置
  - 添加小程序 API 代理规则
- [ ] **T12.2.2** 微信小程序后台配置
  - 服务器域名白名单
  - 业务域名配置
- [ ] **T12.2.3** 提交审核发布

---

## 任务优先级说明

| 优先级 | 阶段 | 说明 |
|-------|------|-----|
| P0 (必须) | Phase 1-6 | 核心功能：认证、商品、购物车、订单、地址 |
| P1 (重要) | Phase 7-10 | 增强功能：收藏、消息、AI客服、反馈 |
| P2 (优化) | Phase 11 | 前端 UI 完善 |
| P3 (完善) | Phase 12 | 测试、部署、上线 |

## 预估工作量

| 阶段 | 任务数 | 复杂度 |
|-----|-------|-------|
| Phase 1: 基础架构 | 8 | 中 |
| Phase 2: 用户认证 | 6 | 低 |
| Phase 3: 商品模块 | 7 | 中 |
| Phase 4: 购物车 | 6 | 低 |
| Phase 5: 订单模块 | 11 | 高 |
| Phase 6: 地址管理 | 5 | 低 |
| Phase 7: 收藏/历史 | 4 | 低 |
| Phase 8: 消息通知 | 5 | 中 |
| Phase 9: AI客服 | 4 | 高 |
| Phase 10: 反馈 | 3 | 低 |
| Phase 11: 前端开发 | 30+ | 高 |
| Phase 12: 测试部署 | 6 | 中 |

**总计**: 约 95+ 个任务项
