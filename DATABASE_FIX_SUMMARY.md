# 数据库优化修复说明

> 创建时间：2026-03-20  
> 问题：跨数据库外键约束导致删除客户失败  
> 解决方案：移除跨数据库外键约束

---

## 🐛 问题描述

在删除客户时出现以下错误：

```
sqlite3.OperationalError: no such table: shipment_records
```

**根本原因**：
- `shipment_records` 表位于 `products.db` 
- `purchase_units` 表位于 `customers.db`
- SQLAlchemy 尝试执行跨数据库的级联删除查询
- SQLite 不支持跨数据库的外键约束和关系查询

---

## ✅ 解决方案

### 1. 修改模型文件

**修改了 [`app/db/models/shipment.py`](file:///e:/FHD/XCAGI/app/db/models/shipment.py)**：
- 移除了 `ForeignKey('purchase_units.id', ondelete='SET NULL')`
- 移除了 `relationship("PurchaseUnit", back_populates="shipments")`
- 保留 `unit_id` 字段作为普通整数列

**修改了 [`app/db/models/purchase_unit.py`](file:///e:/FHD/XCAGI/app/db/models/purchase_unit.py)**：
- 移除了 `relationship("ShipmentRecord", back_populates="purchase_unit_ref")`
- 添加注释说明跨数据库关系不支持

### 2. 创建迁移脚本

**新建迁移脚本**: [`alembic/versions/9e007d030e13_remove_cross_database_fk.py`](file:///e:/FHD/XCAGI/alembic/versions/9e007d030e13_remove_cross_database_fk.py)

内容：
```python
"""remove_cross_database_fk

说明：移除跨数据库的外键约束
SQLite 不支持跨数据库的外键约束，因为 shipment_records 在 products.db 中，
而 purchase_units 在 customers.db 中。
"""
```

### 3. 执行迁移

```bash
cd e:\FHD\XCAGI
python -c "from alembic.config import Config; from alembic import command; command.upgrade(Config('alembic.ini'), 'head')"
```

迁移成功执行，数据库架构已更新。

---

## 📊 当前外键状态

### ✅ 有效的外键约束（6 个）

| 子表 | 父表 | 字段 | 删除策略 | 数据库 |
|------|------|------|---------|--------|
| sessions | users | user_id → id | CASCADE | products.db |
| ai_conversation_sessions | users | user_id → id | CASCADE | products.db |
| ai_conversations | ai_conversation_sessions | session_id → session_id | CASCADE | products.db |
| ai_tools | ai_tool_categories | category_id → id | SET NULL | products.db |
| wechat_tasks | wechat_contacts | contact_id → id | CASCADE | products.db |
| wechat_contact_context | wechat_contacts | contact_id → id | CASCADE | products.db |

### ❌ 已移除的外键约束（1 个）

| 子表 | 父表 | 原因 |
|------|------|------|
| ~~shipment_records~~ | ~~purchase_units~~ | 跨数据库不支持 |

---

## 🔍 验证结果

**测试删除客户**：
```bash
cd e:\FHD\XCAGI
python -c "from app.services.customer_import_service import CustomerImportService; service = CustomerImportService(); result = service.delete(3); print(result)"
```

**结果**：
```json
{'success': True, 'message': '客户删除成功', 'deleted_count': 1}
```

✅ 删除功能恢复正常！

---

## ⚠️ 注意事项

### 1. 数据一致性

由于移除了跨数据库外键约束，应用层需要手动维护数据一致性：

- 删除客户时，需要手动处理关联的发货单
- 建议在删除客户前，先查询并处理相关的 `shipment_records`

### 2. 查询关联数据

如果需要查询客户的发货记录，可以使用手动 join：

```python
# 示例：查询某个客户的所有发货单
from sqlalchemy.orm import Session
from app.db.models.shipment import ShipmentRecord
from app.db.models.purchase_unit import PurchaseUnit

with Session() as db:
    customer_id = 1
    shipments = db.query(ShipmentRecord).filter(
        ShipmentRecord.unit_id == customer_id
    ).all()
```

### 3. 未来改进

如果未来需要完整的跨数据库关系，考虑：
- 合并 `products.db` 和 `customers.db` 为单一数据库
- 或迁移到支持跨数据库约束的数据库（如 PostgreSQL）

---

## 📝 相关文件

1. **修复说明**: 本文档
2. **迁移指南**: [`ALEMBIC_MIGRATION_GUIDE.md`](file:///e:/FHD/XCAGI/ALEMBIC_MIGRATION_GUIDE.md)
3. **数据库体检报告**: [`DATABASE_HEALTH_REPORT.md`](file:///e:/FHD/XCAGI/DATABASE_HEALTH_REPORT.md)
4. **测试脚本**: [`test_database_optimization.py`](file:///e:/FHD/XCAGI/test_database_optimization.py)

---

## 🎯 总结

**问题已解决**！

- ✅ 客户删除功能恢复正常
- ✅ 保留了同数据库的外键约束（6 个）
- ✅ 保留了所有索引（11 个）
- ✅ 保留了完整的 Alembic 迁移体系
- ⚠️ 移除了跨数据库外键约束（SQLite 限制）

**建议**：在应用层添加数据一致性检查，确保删除客户前妥善处理关联的发货记录。
