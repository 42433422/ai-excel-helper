# 模板预览页面问题分析

## 问题描述
1. 页面空白或内容不显示
2. 切换单位/筛选后内容消失
3. 点击其他页面后再返回，同样显示空白

## 问题根源分析

### 1. Vue 组件生命周期问题
`TemplatePreviewView.vue` 在 `mounted()` 中加载模板数据：
```javascript
mounted() {
  this.refreshTemplates()
}
```

**问题**：如果使用 Vue Router 的 `keep-alive` 或组件被缓存（这是默认行为），当用户导航到其他页面再返回时：
- 组件不会重新 `mounted`
- `mounted()` 中的 `refreshTemplates()` 不会再次执行
- 页面显示空白

### 2. 状态持久化导致的问题
组件的 `data()` 中设置了默认状态：
```javascript
activeTab: 'all',
templates: [],
loading: false,
```

但如果用户操作后状态改变（如 `activeTab = 'excel'`），这些状态会被保留。当组件重新激活时，如果没有正确刷新数据，会导致显示异常。

### 3. 可能缺少 `activated()` 生命周期钩子
Vue 组件在 `keep-alive` 缓存的组件被重新激活时会调用 `activated()`，而不是 `mounted()`。

---

## 修复方案

### Step 1: 添加 `activated()` 生命周期钩子
```javascript
activated() {
  this.refreshTemplates()
}
```

### Step 2: 确保状态正确重置
在 `refreshTemplates()` 开始时重置可能存在的错误状态。

### Step 3: 添加错误边界和加载状态处理
确保 API 失败时不会导致页面一直空白。

---

## 待确认
1. 前端是否使用了 `keep-alive`？
2. 浏览器 Console 有报错信息吗？
