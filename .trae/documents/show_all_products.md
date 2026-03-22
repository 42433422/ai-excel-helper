# 产品管理页面 - 改为展示全部产品

## 问题描述
当前产品列表分页（每页20条）导致滚动加载时出现各种问题：
- 滚动到底部时跳回顶部
- 加载更多时出现竞态条件
- 用户体验差，需要不断滚动加载

## 解决方案
将产品列表改为**一次性加载全部产品**，不再分页。

## 修改内容

### 1. ProductsView.vue - 移除分页限制
**文件**: `frontend/src/views/ProductsView.vue`

```javascript
const perPage = ref(20);  // 改为 1000 或更大
```

或者更彻底地，直接请求全部数据：
```javascript
const loadProducts = async (reset = true) => {
  const params = { page: 1, per_page: 1000 };  // 一次性加载1000条
  if (searchQuery.value) params.keyword = searchQuery.value;
  if (selectedUnit.value) params.unit = selectedUnit.value;
  // ... 直接加载全部，不考虑分页
  hasMore.value = false;  // 禁用加载更多
};
```

### 2. 隐藏/禁用滚动加载更多功能
DataTable 组件的 `hasMore` 设为 false 时，不会触发滚动加载。

---

## 实施步骤
1. 修改 `ProductsView.vue` 的 `loadProducts` 函数
2. 移除 `loadMoreProducts` 的调用或始终设置 `hasMore = false`
3. 将 `per_page` 设为较大值（如 1000）
