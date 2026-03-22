---
name: "db-query"
description: "数据库查询工具，支持查询产品、客户、发货记录等数据。Invoke when user asks to query database, search products, find customers, or check shipment records."
---

# Database Query Skill

数据库查询工具，提供对系统中各类数据的查询功能。

## 可查询的数据表

| 表名 | 说明 | 主要字段 |
|------|------|----------|
| products | 产品表 | model_number, name, specification, price, quantity |
| customers | 客户表 | customer_name, contact_person, contact_phone |
| shipment_records | 发货记录 | customer_id, created_at, products |
| materials | 材料表 | name, category, unit, price |

## 使用方法

### 1. 使用上下文管理器查询

```python
from app.services.database_service import with_db_session

@with_db_session
def query_products(db, name_like=None):
    from app.db.models import Product
    query = db.query(Product)
    if name_like:
        query = query.filter(Product.name.like(f'%{name_like}%'))
    return query.limit(20).all()
```

### 2. 直接使用Session查询

```python
from app.db import SessionLocal
from app.db.models import Product

db = SessionLocal()
try:
    products = db.query(Product).limit(20).all()
    for p in products:
        print(f'{p.model_number} - {p.name} - ¥{p.price}')
finally:
    db.close()
```

### 3. 模糊搜索产品

```python
from app.db import SessionLocal
from app.db.models import Product

db = SessionLocal()
try:
    results = db.query(Product).filter(
        Product.name.like('%关键词%')
    ).all()
finally:
    db.close()
```

## 功能列表

| 功能 | 触发场景 |
|------|----------|
| 查询所有产品 | 用户说"查看产品"、"查询产品" |
| 按名称搜索 | 用户说"搜索XX产品"、"找XX" |
| 按型号查询 | 用户说"型号XX"、"产品编号XX" |
| 查询客户 | 用户说"查看客户"、"搜索客户" |
| 发货记录查询 | 用户说"发货记录"、"最近发货" |
| 价格查询 | 用户说"XX价格"、"多少钱" |

## 示例查询

### 查询所有产品（前20条）
```python
db.query(Product).limit(20).all()
```

### 按产品名称模糊搜索
```python
db.query(Product).filter(
    Product.name.like('%白色%')
).all()
```

### 查询客户信息
```python
db.query(Customer).filter(
    Customer.customer_name.like('%关键词%')
).all()
```

### 按时间范围查询发货记录
```python
from datetime import datetime, timedelta
start_date = datetime.now() - timedelta(days=30)
db.query(ShipmentRecord).filter(
    ShipmentRecord.created_at >= start_date
).all()
```