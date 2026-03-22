# 产品管理页面单位筛选问题修复计划

## 问题描述
用户选择了产品单位后，页面显示的数据没有变化，且只显示 20 条数据就提示"没有更多数据了"。

## 问题根源

### 问题1: Service 层 total 计算错误
**文件**: `app/services/products_service.py`

```python
def get_products(self, unit_name, ...):
    products = self._repository.find_all(...)
    return {
        "total": len(products),  # BUG: 返回的是当前页数量，不是过滤后的总数！
        "count": len(products)
    }
```

**后果**: 七彩乐园有 61 个产品，但 API 返回 `total: 20`，导致前端判断 `hasMore = false`，无法加载更多。

### 问题2: 前端可能未发送 unit 参数
需要确认前端选择单位后是否正确发送 `unit` 参数。

## 修复方案

### Step 1: 修复 Service 层 - 添加正确的总数统计
**文件**: `app/services/products_service.py`

修改 `get_products` 方法：
- 添加 `count()` 方法调用获取过滤后的总数
- 返回正确的 `total` 值

### Step 2: 验证修复
- 重启后端服务
- 测试单位筛选和分页功能
