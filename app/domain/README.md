# DDD 领域层

此目录包含 XCAGI 系统的领域模型，按照 DDD（领域驱动设计）原则组织。

## 目录结构

```
domain/
├── __init__.py
├── shipment/          # 发货单领域 (核心领域)
│   ├── __init__.py
│   ├── entities.py   # 发货单项实体
│   ├── value_objects.py  # 值对象 (订单号、金额、数量)
│   └── aggregates.py # 发货单聚合根
├── product/           # 产品领域
│   ├── __init__.py
│   ├── entities.py   # 产品实体
│   └── value_objects.py  # 值对象
└── customer/          # 客户领域
    ├── __init__.py
    ├── entities.py   # 客户/购买单位实体
    └── value_objects.py  # 值对象
```

## 领域概念

### 核心领域 (Core Domain)
- **Shipment (发货单)**: 系统的核心业务对象，代表一次发货业务

### 支持领域 (Supporting Domain)
- **Product (产品)**: 产品信息管理
- **Customer (客户)**: 客户和购买单位管理

## 设计原则

1. **以业务为中心**: 代码反映业务概念，而非技术实现
2. **单一职责**: 每个类只有一个改变的理由
3. **充血模型**: 领域对象包含业务逻辑，而非简单的数据容器
4. **聚合根**: 通过聚合根维护领域对象的一致性
