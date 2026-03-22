# 产品管理页面滚动刷新问题排查

## 当前滚动加载逻辑

### DataTable.vue 滚动处理
```javascript
const handleScroll = () => {
  if (!tableWrapper.value || props.loading || !props.hasMore) return

  const { scrollTop, scrollHeight, clientHeight } = tableWrapper.value
  const threshold = 100

  if (scrollHeight - scrollTop - clientHeight < threshold) {
    emit('load-more')
  }
}
```

### ProductsView.vue 加载更多
```javascript
const loadMoreProducts = async () => {
  if (loading.value || !hasMore.value) return
  await loadProducts(false)
}

const loadProducts = async (reset = true) => {
  // ... 构建参数
  const result = await store.fetchProducts(params)
  if (result && result.data) {
    if (reset) {
      products.value = result.data
    } else {
      products.value = [...products.value, ...result.data]
    }
    hasMore.value = products.value.length < (result.total || 0)
    currentPage.value++
  }
}
```

## 可能的问题原因

### 1. 滚动阈值过于敏感
- 当前阈值是 100px，当用户滚动到距离底部 100px 时就触发加载
- 如果数据刚好 20 条填满表格，用户滚动时可能一直触發

### 2. 可能的竞态条件
- `loadMoreProducts` 检查 `loading` 状态，但如果异步操作还没开始时又有滚动事件

### 3. 前端请求被拦截或失败
- 如果 API 请求返回错误可能导致页面状态异常

## 建议的修复方案

### 方案：添加防抖 (debounce) 或锁
在 `loadMoreProducts` 中添加锁机制，防止重复触发：

```javascript
let isLoadingMore = false

const loadMoreProducts = async () => {
  if (loading.value || !hasMore.value || isLoadingMore) return
  isLoadingMore = true
  try {
    await loadProducts(false)
  } finally {
    isLoadingMore = false
  }
}
```

---

## 待确认
请告诉我是哪种情况：
1. 滚动到**底部附近**才刷新？还是**稍微滚动**就刷新？
2. 刷新后页面是**完全重新加载**（白屏）还是**只是数据更新**？
3. 浏览器 Console 有**错误信息**吗？
