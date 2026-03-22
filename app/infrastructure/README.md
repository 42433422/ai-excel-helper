# 基础设施层 - 仓储实现

此目录包含 DDD 架构的基础设施层实现，主要负责：
- 数据库持久化
- ORM 映射
- 外部服务调用

```
infrastructure/
├── repositories/      # 数据仓储
│   ├── shipment_repository.py
│   ├── product_repository.py
│   └── customer_repository.py
└── persistence/       # 持久化相关
```
