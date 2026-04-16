# 工具函数使用指南

## 网络请求 (utils/request.js)

### GET 请求
```javascript
const { get } = require('../../utils/request')

const res = await get('/products/list', { page: 1, per_page: 10 })
```

### POST 请求
```javascript
const { post } = require('../../utils/request')

const res = await post('/orders/create', orderData)
```

### PUT 请求
```javascript
const { put } = require('../../utils/request')

const res = await put('/user/profile', userData)
```

### DELETE 请求
```javascript
const { del } = require('../../utils/request')

const res = await del(`/favorites/${productId}`)
```

## 支付工具 (utils/payment.js)

### 发起支付
```javascript
const { requestPayment } = require('../../utils/payment')

try {
  await requestPayment({
    orderId: 'ORD123456',
    amount: 9900, // 单位：分
    description: '商品名称'
  })
  console.log('支付成功')
} catch (error) {
  if (error.code === 'cancel') {
    console.log('用户取消支付')
  } else {
    console.log('支付失败')
  }
}
```

### 查询支付结果
```javascript
const { queryPaymentResult } = require('../../utils/payment')

const res = await queryPaymentResult('ORD123456')
```

### 申请退款
```javascript
const { requestRefund } = require('../../utils/payment')

const res = await requestRefund({
  orderId: 'ORD123456',
  amount: 9900,
  reason: '商品质量问题'
})
```

## 收藏工具 (utils/favorite.js)

### 获取收藏列表
```javascript
const { getFavorites } = require('../../utils/favorite')

const favorites = getFavorites()
```

### 添加收藏
```javascript
const { addFavorite } = require('../../utils/favorite')

const success = addFavorite({
  id: 123,
  name: '商品名称',
  image: 'https://...',
  price: 99.00
})
```

### 取消收藏
```javascript
const { removeFavorite } = require('../../utils/favorite')

removeFavorite(123)
```

### 检查是否已收藏
```javascript
const { isFavorite } = require('../../utils/favorite')

const favorited = isFavorite(123)
```

## 分享工具 (utils/share.js)

### 商品分享
```javascript
const { shareProduct } = require('../../utils/share')

// 在页面的 onShareAppMessage 中使用
onShareAppMessage() {
  return shareProduct(this.data.product)
}
```

### 生成分享数据
```javascript
const { generateShareData } = require('../../utils/share')

const shareData = generateShareData({
  type: 'product',
  data: {
    id: 123,
    name: '商品名称',
    image: 'https://...'
  }
})
```

### 显示分享菜单
```javascript
const { showShareMenu } = require('../../utils/share')

showShareMenu({
  type: 'product',
  data: product,
  copyLink: true // 同时复制链接
})
```

## 骨架屏工具 (utils/skeleton.js)

### 获取骨架屏数据
```javascript
const { getSkeletonData } = require('../../utils/skeleton')

// 列表骨架屏
const listData = getSkeletonData('list')

// 详情页骨架屏
const detailData = getSkeletonData('detail')

// 购物车骨架屏
const cartData = getSkeletonData('cart')
```

### 使用骨架屏组件
```xml
<skeleton isLoading="{{loading}}" type="list" count="6"></skeleton>

<!-- 或使用插槽方式 -->
<view wx:if="{{loading}}">
  <skeleton type="list"></skeleton>
</view>
<view wx:else>
  <!-- 实际内容 -->
</view>
```

## 图片工具 (utils/image.js)

### 图片预加载
```javascript
const { preloadImages } = require('../../utils/image')

await preloadImages([
  'https://...',
  'https://...'
])
```

### 观察图片（懒加载）
```javascript
const { observeImage } = require('../../utils/image')

observeImage('.my-image', () => {
  console.log('图片进入可视区域')
})
```

### 清除观察器
```javascript
const { clearObserver } = require('../../utils/image')

clearObserver()
```

## 通用工具 (utils/util.js)

### 格式化价格
```javascript
const { formatPrice } = require('../../utils/util')

const price = formatPrice(299) // ¥299.00
```

### 格式化日期
```javascript
const { formatDate } = require('../../utils/util')

const date = formatDate(new Date()) // 2024-01-01 12:00
const date2 = formatDate(new Date(), 'YYYY-MM-DD') // 2024-01-01
```

### 验证手机号
```javascript
const { validatePhone } = require('../../utils/util')

const valid = validatePhone('13800138000') // true
```

### 防抖函数
```javascript
const { debounce } = require('../../utils/util')

const searchFunc = debounce((keyword) => {
  console.log('搜索:', keyword)
}, 300)

// 调用
searchFunc('keyword')
```

### 节流函数
```javascript
const { throttle } = require('../../utils/util')

const scrollFunc = throttle(() => {
  console.log('滚动中')
}, 100)

// 调用
scrollFunc()
```

## 登录状态管理

### 设置 Token
```javascript
const app = getApp()
app.setToken('your-token')
```

### 清除 Token
```javascript
const app = getApp()
app.clearToken()
```

### 检查登录状态
```javascript
const app = getApp()

if (app.globalData.isLoggedIn) {
  // 已登录
} else {
  // 未登录，跳转到登录页
  wx.navigateTo({
    url: '/pages/login/login'
  })
}
```

### 显示加载提示
```javascript
const app = getApp()

app.showLoading('加载中...')

// 执行操作
await someAsyncOperation()

app.hideLoading()
```

## 注意事项

1. **异步操作**: 所有网络请求都使用 Promise，建议使用 async/await
2. **错误处理**: 使用 try-catch 处理可能的错误
3. **Token 管理**: Token 会自动添加到请求头，无需手动处理
4. **本地存储**: 收藏、购物车等数据支持本地存储，离线可用
5. **分包加载**: 订单和个人中心页面已分包，注意页面路径

## 示例：完整的购买流程

```javascript
// 1. 检查登录状态
const app = getApp()
if (!app.globalData.isLoggedIn) {
  wx.navigateTo({ url: '/pages/login/login' })
  return
}

// 2. 创建订单
const { post } = require('../../utils/request')
const orderRes = await post('/orders/create', {
  products: cartItems,
  address_id: addressId
})

// 3. 发起支付
const { requestPayment } = require('../../utils/payment')
try {
  await requestPayment({
    orderId: orderRes.data.id,
    amount: orderRes.data.amount,
    description: orderRes.data.product_name
  })
  
  // 支付成功，跳转
  wx.redirectTo({
    url: `/pages/order/result/result?type=success&id=${orderRes.data.id}`
  })
} catch (error) {
  if (error.code === 'cancel') {
    wx.showToast({ title: '已取消支付', icon: 'none' })
  } else {
    wx.showModal({
      title: '支付失败',
      content: error.message,
      showCancel: false
    })
  }
}
```
