# Alembic 数据库迁移使用指南

> 项目：XCAGI  
> 创建时间：2026-03-20  
> 版本：1.0

---

## 📋 概述

本项目已配置完整的 Alembic 数据库迁移体系，包含：
- ✅ 7 个外键约束（Sessions, AI, WeChat, Shipment 模块）
- ✅ 5 个额外索引（优化查询性能）
- ✅ 完整的模型关系映射（relationship）

---

## 🚀 快速开始

### 1. 查看当前数据库版本

```bash
cd e:\FHD\XCAGI
python -c "from alembic.config import Config; from alembic import command; command.current(Config('alembic.ini'))"
```

### 2. 升级到最新版本

```bash
cd e:\FHD\XCAGI
python -c "from alembic.config import Config; from alembic import command; command.upgrade(Config('alembic.ini'), 'head')"
```

### 3. 回滚到上一个版本

```bash
cd e:\FHD\XCAGI
python -c "from alembic.config import Config; from alembic import command; command.downgrade(Config('alembic.ini'), '-1')"
```

---

## 📝 迁移脚本列表

当前项目包含以下迁移脚本（按执行顺序）：

| 版本号 | 描述 | 依赖版本 | 状态 |
|-------|------|---------|------|
| `202d63cb1c33` | initial_schema - 初始架构 | (none) | ✅ |
| `a7d310349a7d` | add_recommended_indexes - 添加推荐索引 | 202d63cb1c33 | ✅ |
| `8d4b53946b72` | add_foreign_key_constraints_sessions_and_ai | a7d310349a7d | ✅ |
| `66ee10160629` | add_foreign_key_constraints_wechat | 8d4b53946b72 | ✅ |
| `0ca9c7759440` | add_foreign_key_constraints_shipment | 66ee10160629 | ✅ |
| `ba97c759c51d` | add_additional_indexes | 0ca9c7759440 | ✅ |
| `9e007d030e13` | remove_cross_database_fk - 移除跨数据库外键 | ba97c759c51d (head) | ✅ |

---

## 🔧 常用命令

### 查看迁移历史

```bash
cd e:\FHD\XCAGI
python -c "from alembic.config import Config; from alembic import command; command.history(Config('alembic.ini'))"
```

### 生成新的迁移脚本

```bash
cd e:\FHD\XCAGI
python -c "from alembic.config import Config; from alembic import command; command.revision(Config('alembic.ini'), autogenerate=True, message='你的迁移描述')"
```

### 检查当前版本与模型差异

```bash
cd e:\FHD\XCAGI
python -c "from alembic.config import Config; from alembic import command; command.check(Config('alembic.ini'))"
```

### 验证外键约束

```python
import sqlite3

conn = sqlite3.connect('products.db')

# 检查 sessions 表的外键
result = conn.execute('PRAGMA foreign_key_list(sessions)')
print("Sessions 表的外键:")
for row in result.fetchall():
    print(f"  {row}")

# 检查索引
result = conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
print("\n所有索引:")
for row in result.fetchall():
    print(f"  {row[0]}")
```

---

## 📊 外键约束详情

### 已创建的外键关系

| 子表 | 父表 | 字段 | 删除策略 | 说明 |
|------|------|------|---------|------|
| `sessions` | `users` | user_id → id | CASCADE | ✅ 同数据库 |
| `ai_conversation_sessions` | `users` | user_id → id | CASCADE | ✅ 同数据库 |
| `ai_conversations` | `ai_conversation_sessions` | session_id → session_id | CASCADE | ✅ 同数据库 |
| `ai_tools` | `ai_tool_categories` | category_id → id | SET NULL | ✅ 同数据库 |
| `wechat_tasks` | `wechat_contacts` | contact_id → id | CASCADE | ✅ 同数据库 |
| `wechat_contact_context` | `wechat_contacts` | contact_id → id | CASCADE | ✅ 同数据库 |
| ~~`shipment_records`~~ | ~~`purchase_units`~~ | ~~unit_id → id~~ | ~~SET NULL~~ | ❌ **已移除** - 跨数据库不支持 |

### ⚠️ 跨数据库限制

**重要说明**：SQLite 不支持跨数据库的外键约束。

- `shipment_records` 表在 `products.db` 中
- `purchase_units` 表在 `customers.db` 中
- 因此无法在这两个表之间创建外键约束
- 应用层需要手动维护数据一致性

### 外键策略说明

- **CASCADE**: 删除父记录时，自动删除所有子记录
- **SET NULL**: 删除父记录时，将子记录的外键字段设为 NULL
- **NO ACTION**: 如果有子记录存在，禁止删除父记录

---

## 📈 索引详情

### 已创建的索引

| 索引名称 | 表 | 字段 | 用途 |
|---------|-----|------|------|
| `idx_shipment_records_status_date` | shipment_records | status, created_at | 按状态查询发货单 |
| `idx_ai_conversations_session_date` | ai_conversations | session_id, created_at | 查询会话对话记录 |
| `idx_products_category_active` | products | category, is_active | 产品分类筛选 |
| `idx_wechat_tasks_status_updated` | wechat_tasks | status, updated_at | 任务状态更新查询 |
| `idx_sessions_expires` | sessions | expires_at | 会话过期清理 |
| `idx_shipment_records_unit_date` | shipment_records | purchase_unit, created_at | 已存在（a7d310349a7d） |
| `idx_shipment_records_created` | shipment_records | created_at | 已存在（a7d310349a7d） |
| `idx_purchase_units_name_active` | purchase_units | unit_name, is_active | 已存在（a7d310349a7d） |
| `idx_products_model` | products | model_number | 已存在（a7d310349a7d） |
| `idx_products_name` | products | name | 已存在（a7d310349a7d） |
| `idx_wechat_contacts_type_active` | wechat_contacts | contact_type, is_active | 已存在（a7d310349a7d） |

---

## 🧪 运行测试

### 完整测试套件

```bash
cd e:\FHD\XCAGI
python test_database_optimization.py
```

测试内容包括：
- ✅ 外键约束存在性验证
- ✅ 索引存在性验证
- ✅ 级联删除功能测试
- ✅ Alembic 迁移状态验证

### 手动测试外键约束

```python
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.db.models.user import User, Session as UserSession
from datetime import datetime, timedelta

db = SessionLocal()

try:
    # 创建用户
    user = User(username="test_fk", password="hashed")
    db.add(user)
    db.commit()
    
    # 创建会话
    session = UserSession(
        session_id="test_fk_session",
        user_id=user.id,
        expires_at=datetime.now() + timedelta(days=1)
    )
    db.add(session)
    db.commit()
    
    # 尝试删除用户（应该级联删除会话）
    db.delete(user)
    db.commit()
    
    # 验证会话已被删除
    remaining = db.query(UserSession).filter_by(session_id="test_fk_session").first()
    assert remaining is None, "级联删除失败"
    print("✓ 外键约束工作正常")
    
except Exception as e:
    print(f"✗ 测试失败：{e}")
    db.rollback()
finally:
    db.close()
```

---

## ⚠️ 注意事项

### 1. 数据备份

在执行任何迁移之前，务必备份数据库：

```bash
# Windows PowerShell
Copy-Item products.db products.db.backup
Copy-Item customers.db customers.db.backup
```

### 2. 生产环境迁移

生产环境迁移步骤：

1. **备份数据库**
2. **在测试环境验证迁移**
3. **暂停应用服务**
4. **执行迁移**: `alembic upgrade head`
5. **验证迁移结果**
6. **恢复服务**

### 3. 回滚策略

如果需要回滚：

```bash
# 回滚一步
alembic downgrade -1

# 回滚到指定版本
alembic downgrade <revision_id>

# 回滚到初始状态
alembic downgrade base
```

### 4. 处理迁移冲突

如果多个开发者创建了迁移脚本，可能导致版本冲突：

```bash
# 查看迁移树
alembic heads

# 如果有多个 head，需要合并
# 手动编辑迁移脚本，调整 down_revision
# 然后重新生成迁移
```

---

## 🔍 故障排查

### 问题 1: 迁移失败

**症状**: 执行 `alembic upgrade head` 时报错

**解决方案**:
1. 检查错误日志
2. 查看数据库当前版本：`alembic current`
3. 尝试手动修复迁移脚本
4. 如果数据不重要，可以重置迁移历史

### 问题 2: 外键约束不生效

**症状**: 插入违反外键约束的数据没有报错

**解决方案**:
```sql
-- 确保外键已启用
PRAGMA foreign_keys = ON;

-- 检查外键是否已创建
PRAGMA foreign_key_list(表名);
```

### 问题 3: 模型与数据库不同步

**症状**: `alembic check` 显示差异

**解决方案**:
```bash
# 生成新的迁移脚本
alembic revision --autogenerate -m "sync_models"

# 审查生成的脚本
# 执行迁移
alembic upgrade head
```

---

## 📚 参考资源

- [Alembic 官方文档](https://alembic.sqlalchemy.org/)
- [SQLAlchemy ORM 关系](https://docs.sqlalchemy.org/orm/relationship_api.html)
- [SQLite 外键约束](https://www.sqlite.org/foreignkeys.html)

---

## 📞 技术支持

如有问题，请查看：
1. 项目文档：`DATABASE_HEALTH_REPORT.md`
2. 优化计划：`database_optimization_plan.md`
3. 测试脚本：`test_database_optimization.py`
