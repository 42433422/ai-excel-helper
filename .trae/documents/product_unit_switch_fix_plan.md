# 产品管理页面单位切换问题修复计划

## 问题描述
前端产品管理页面无法根据"产品单位"下拉选择进行数据切换，无论选择哪个单位，显示的数据都是一样的。

## 问题根源分析

### 实际数据结构确认
**数据库 products 表的实际字段**：
```
['id', 'model_number', 'name', 'specification', 'price', 'quantity',
 'description', 'category', 'brand', 'unit', 'is_active', 'created_at', 'updated_at']
```

**重要发现**：数据库的 `products.unit` 字段存储的是**"产品单位"（客户名称）**，不是计量单位！

示例数据：
```
{'id': 2453, 'name': 'PU白底漆', 'model_number': 'GS372', 'unit': '半岛风情', 'price': 11.5}
{'id': 2454, 'name': 'PU底漆固化剂', 'model_number': 'GS309', 'unit': '半岛风情', 'price': 15.0}
{'id': 2455, 'name': 'PU哑光奶白色漆', 'model_number': '干板样', 'unit': '半岛风情', 'price': 15.0}
```

### 问题链路追踪

1. **前端 `ProductsView.vue` (L142-150)** ✅
   - 正确传递 `unit` 参数：`params.unit = selectedUnit.value`
   - 调用 `store.fetchProducts(params)` 发送请求

2. **后端路由 `routes/products.py` (L76-105)** ✅
   - 正确接收 `unit_name = request.args.get("unit")`
   - 正确调用 `service.get_products(unit_name=unit_name, ...)`

3. **Service 层 `services/products_service.py` (L29-57)** ✅
   - 正确传递 `unit_name` 给 `repository.find_all(unit_name=unit_name, ...)`

4. **Repository 层 `product_repository_impl.py` (L70-76)** ❌ **核心问题！**
   ```python
   def find_all(self, page: int = 1, per_page: int = 20, **kwargs) -> List[Product]:
       # **BUG: 完全忽略了 unit_name 和 keyword 参数！**
       models = db.query(ProductModel).order_by(
           ProductModel.id.desc()
       ).limit(per_page).offset(offset).all()
       return [self._to_domain(m) for m in models]
   ```

### 根本原因
Repository 的 `find_all` 方法签名中有 `**kwargs`，接收了 `unit_name` 和 `keyword` 参数，但**完全没有使用它们**！

---

## 修复方案

### Step 1: 修改 Repository 实现 - 添加过滤逻辑
**文件**: `app/infrastructure/repositories/product_repository_impl.py`

修改 `find_all` 方法，添加：
- `unit_name` 过滤：`ProductModel.unit == unit_name`
- `keyword` 过滤：`OR(ProductModel.name.like(...), ProductModel.model_number.like(...))`

### Step 2: 验证修复
- 重启后端服务
- 测试单位切换功能

---

## 注意事项
- 需要重启后端服务使修改生效
- 搜索功能（按型号或名称）也会一并修复
