# DDD 服务迁移执行计划

## 📋 迁移目标

将 `app/services/` 目录下的服务迁移到 DDD 分层架构：
- **Domain 层**：`app/domain/services/` - 领域服务（无状态业务逻辑）
- **Application 层**：`app/application/` - 应用服务（用例编排）
- **Infrastructure 层**：`app/infrastructure/` - 基础设施（技术实现）
- **AI Engines**：`app/ai_engines/` - AI 模型服务
- **Utils**：`app/utils/` - 通用工具

**最终目标**：删除 `app/services/` 目录，确保 routes 只调用 application 层

---

## 📊 当前分析

### Routes 层直接调用 services 的文件（6 个）

| 路由文件 | 调用的服务 | 目标位置 |
|---------|-----------|---------|
| `ai_chat.py` | `ai_conversation_service`, `intent_service` | Application / Domain |
| `ai_parse.py` | `ai_product_parser` | Application |
| `auth.py` | `user_service` | Application |
| `conversations.py` | `conversation_service`, `user_preference_service` | Application |
| `products.py` | `products_service` | Application |
| `wechat.py` | `wechat_task_service` | Application |

### 其他路由文件（通过函数内 import 调用）

| 路由文件 | 调用的服务 | 处理方式 |
|---------|-----------|---------|
| `ai_assistant_compat.py` | `printer_service`, `tts_service` | Application |
| `health.py` | `unified_intent_recognizer` | Domain |
| `intent.py` | `bert_intent_service` | AI Engines |
| `ocr.py` | `ocr_service` | Application |
| `print.py` | `printer_service` | Application |
| `skills.py` | `skills/*` | 保留原位置 |
| `templates.py` | `skills/*` | 保留原位置 |
| `tools.py` | `database_service`, `system_service`, `task_context_service`, `skills/*` | 工具服务 |

---

## 🔄 服务分类

### 第一类：应用服务（迁移到 `app/application/`）

| 原位置 | 目标位置 | 状态 |
|-------|---------|------|
| `services/conversation_service.py` | `application/conversation_app_service.py` | 新建 |
| `services/user_preference_service.py` | `application/user_preference_app_service.py` | 新建 |
| `services/user_service.py` | `application/user_app_service.py` | 新建 |
| `services/auth_service.py` | `application/auth_app_service.py` | 新建 |
| `services/wechat_task_service.py` | `application/wechat_task_app_service.py` | 新建 |

### 第二类：领域服务（迁移到 `app/domain/services/`）

| 原位置 | 目标位置 | 状态 |
|-------|---------|------|
| `services/intent_confirmation_service.py` | `domain/services/intent_confirmation_service.py` | 新建 |
| `services/unified_intent_recognizer.py` | `domain/services/unified_intent_recognizer.py` | 新建 |

### 第三类：基础设施（迁移到 `app/infrastructure/`）

| 原位置 | 目标位置 | 状态 |
|-------|---------|------|
| `services/session_service.py` | `infrastructure/session/session_manager.py` | 新建 |

### 第四类：工具服务（迁移到 `app/utils/`）

| 原位置 | 目标位置 | 状态 |
|-------|---------|------|
| `services/task_context_service.py` | `utils/task_context.py` | 新建 |
| `services/user_memory_service.py` | `utils/user_memory.py` | 新建 |
| `services/system_service.py` | `utils/system_service.py` | 新建 |
| `services/database_service.py` | `utils/database_service.py` | 新建 |

### 第五类：AI 引擎（迁移到 `app/ai_engines/`）

| 原位置 | 目标位置 | 状态 |
|-------|---------|------|
| `services/bert_intent_service.py` | `ai_engines/bert/intent_service.py` | 新建 |
| `services/deepseek_intent_service.py` | `ai_engines/deepseek/intent_service.py` | 新建 |
| `services/rasa_nlu_service.py` | `ai_engines/rasa/nlu_service.py` | 新建 |
| `services/distilled_intent_service.py` | `ai_engines/distilled/intent_service.py` | 新建 |
| `services/intent_trainer.py` | `ai_engines/trainer/intent_trainer.py` | 新建 |
| `services/distillation_trainer.py` | `ai_engines/trainer/distillation_trainer.py` | 新建 |
| `services/distillation_data_collector.py` | `ai_engines/trainer/data_collector.py` | 新建 |

### 第六类：保留原位置

| 原位置 | 说明 |
|-------|------|
| `services/skills/*` | 工具服务，保留原位置 |
| `services/intent_service.py` | 已迁移到 `domain/services/intent/` |
| `services/hybrid_intent_service.py` | 已迁移到 `domain/services/intent/` |
| `services/rule_engine.py` | 已迁移到 `domain/services/` |
| `services/pricing_engine.py` | 已迁移到 `domain/services/` |
| `services/shipment_rules_engine.py` | 已迁移到 `domain/services/` |

---

## 🚀 执行步骤

### 阶段 1：创建新目录结构和端口接口

```bash
# 1. 创建 Infrastructure 层目录
app/infrastructure/session/
app/infrastructure/session/__init__.py

# 2. 创建 AI Engines 层目录
app/ai_engines/bert/
app/ai_engines/deepseek/
app/ai_engines/rasa/
app/ai_engines/distilled/
app/ai_engines/trainer/

# 3. 创建 Domain Services 目录（如果不存在）
app/domain/services/intent_confirmation/
app/domain/services/unified_recognizer/
```

### 阶段 2：迁移工具服务到 Utils

1. `task_context_service.py` → `utils/task_context.py`
2. `user_memory_service.py` → `utils/user_memory.py`
3. `system_service.py` → `utils/system_service.py`
4. `database_service.py` → `utils/database_service.py`

### 阶段 3：迁移基础设施服务

1. `session_service.py` → `infrastructure/session/session_manager.py`

### 阶段 4：迁移 AI 引擎服务

1. `bert_intent_service.py` → `ai_engines/bert/intent_service.py`
2. `deepseek_intent_service.py` → `ai_engines/deepseek/intent_service.py`
3. `rasa_nlu_service.py` → `ai_engines/rasa/nlu_service.py`
4. `distilled_intent_service.py` → `ai_engines/distilled/intent_service.py`
5. `intent_trainer.py` → `ai_engines/trainer/intent_trainer.py`
6. `distillation_trainer.py` → `ai_engines/trainer/distillation_trainer.py`
7. `distillation_data_collector.py` → `ai_engines/trainer/data_collector.py`

### 阶段 5：迁移领域服务

1. `intent_confirmation_service.py` → `domain/services/intent_confirmation_service.py`
2. `unified_intent_recognizer.py` → `domain/services/unified_intent_recognizer.py`

### 阶段 6：迁移/创建应用服务

1. `conversation_service.py` → `application/conversation_app_service.py`
2. `user_preference_service.py` → `application/user_preference_app_service.py`
3. `user_service.py` → `application/user_app_service.py`
4. `auth_service.py` → `application/auth_app_service.py`
5. `wechat_task_service.py` → `application/wechat_task_app_service.py`

### 阶段 7：更新 Routes 层导入

逐个修改路由文件，将 `from app.services` 改为 `from app.application`：

1. `ai_chat.py`
2. `ai_parse.py`
3. `auth.py`
4. `conversations.py`
5. `products.py`
6. `wechat.py`
7. `ai_assistant_compat.py`
8. `health.py`
9. `intent.py`
10. `ocr.py`
11. `print.py`
12. `tools.py`

### 阶段 8：更新 Bootstrap 依赖注入

更新 `app/bootstrap.py`，添加新服务的依赖注入。

### 阶段 9：更新 Application 层 `__init__.py`

更新 `app/application/__init__.py`，导出新服务。

### 阶段 10：删除旧的 services 目录

确认所有迁移完成后，删除 `app/services/` 目录（保留 `services/skills/`）。

---

## ⚠️ 注意事项

### 1. 保持向后兼容
- 在迁移过程中，保持原有的函数名和参数签名
- 使用 `deprecated` 警告提示用户使用新位置

### 2. 循环依赖处理
- `auth_service.py` 依赖 `session_service.py`，需要先迁移 `session_service.py`
- `ai_conversation_service.py` 依赖 `user_memory_service.py`，需要先迁移 `user_memory_service.py`

### 3. 测试验证
- 每迁移一个服务，运行相关测试
- 确保 API 响应格式不变

### 4. 导入路径更新
- 所有 `from app.services` 需要更新为新路径
- 使用 IDE 的全局搜索替换功能

---

## 📅 时间估算

| 阶段 | 工作量 | 风险 |
|------|--------|------|
| 阶段 1: 目录结构 | 0.5 天 | 低 |
| 阶段 2: Utils 迁移 | 1 天 | 低 |
| 阶段 3: Infrastructure 迁移 | 0.5 天 | 低 |
| 阶段 4: AI Engines 迁移 | 1.5 天 | 中 |
| 阶段 5: Domain Services 迁移 | 0.5 天 | 低 |
| 阶段 6: Application 迁移 | 2 天 | 中 |
| 阶段 7: Routes 更新 | 1 天 | 高 |
| 阶段 8-9: Bootstrap 和 __init__ | 0.5 天 | 中 |
| 阶段 10: 删除旧目录 | 0.5 天 | 低 |
| **总计** | **8.5 天** | **中** |

---

## ✅ 验证标准

迁移完成后，检查以下标准：

1. ✅ `grep -r "from app.services" app/routes/` 返回空结果
2. ✅ `grep -r "from app.services" app/application/` 返回空结果
3. ✅ `grep -r "from app.services" app/domain/` 返回空结果
4. ✅ `grep -r "from app.services" app/infrastructure/` 返回空结果
5. ✅ 所有测试通过：`pytest tests/ -v`
6. ✅ 类型检查通过：`mypy app/ --ignore-missing-imports`

---

## 📝 迁移示例

### 示例：conversation_service.py 迁移

**原位置**：`app/services/conversation_service.py`

**目标位置**：`app/application/conversation_app_service.py`

```python
# app/application/conversation_app_service.py

from typing import List, Tuple, Any, Optional
import logging
import uuid
from datetime import datetime

from app.db.session import get_db
from app.db.models import AIConversation, AIConversationSession

logger = logging.getLogger(__name__)


class ConversationApplicationService:
    """对话应用服务类"""

    def __init__(self):
        pass

    def save_message(self, session_id: str, user_id: str, role: str, content: str, intent: str = "", metadata: str = "") -> int:
        # ... 原有逻辑
        pass

    def get_session_messages(self, session_id: str, limit: int = 50) -> List[Tuple]:
        # ... 原有逻辑
        pass

    # ... 其他方法


_conversation_app_service: Optional[ConversationApplicationService] = None


def get_conversation_app_service() -> ConversationApplicationService:
    global _conversation_app_service
    if _conversation_app_service is None:
        _conversation_app_service = ConversationApplicationService()
    return _conversation_app_service
```

**更新 routes/conversations.py**：

```python
# 更新前
from app.services.conversation_service import get_conversation_service
from app.services.user_preference_service import get_user_preference_service

# 更新后
from app.application.conversation_app_service import get_conversation_app_service
from app.application.user_preference_app_service import get_user_preference_app_service
```

---

**下一步**：等待用户确认后开始执行迁移
