# MODstore 通用扩展加载器设计

## 背景

当前主系统的 MOD 扩展点有限（仅支持路由注册、钩子、AI 员工），当新 MOD 需要中间件、定时任务、数据库迁移等能力时，无法通过现有机制对接。

本设计提出一个**通用扩展加载器**，使 MOD 能通过标准化的 manifest 声明任意类型的扩展，主系统按需加载。

---

## 目标

1. MOD 开发者只需在 `manifest.json` 中声明扩展，无需修改主系统
2. 主系统通过**可扩展的加载器注册表**处理不同类型的扩展
3. 新扩展类型只需要在 `app.mod_sdk` 中加一个加载器插件
4. 向后兼容，不破坏现有 MOD 加载逻辑

---

## 架构

```
┌─────────────────────────────────────────────────┐
│                  manifest.json                  │
│                                                 │
│  "extensions": {                                │
│    "middleware": ["auth.py"],                   │
│    "background_tasks": ["tasks.py"],            │
│    "db_migrations": ["migrations/"],            │
│    "event_subscriptions": { ... },             │
│    "service_overrides": { ... }                 │
│  }                                              │
└──────────────────────┬──────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│           Extension Loader Manager              │
│                                                 │
│  1. 解析 manifest.extensions                    │
│  2. 按类型分发到对应 Loader                     │
│  3. 按优先级顺序加载                            │
│  4. 记录加载结果/失败信息                       │
└────┬───────┬───────┬───────┬────────────────────┘
     │       │       │       │
     ▼       ▼       ▼       ▼
┌────────┐┌──────┐┌──────┐┌────────┐
│Middleware││Task  ││DB    ││Override│ ...
│Loader    ││Loader││Loader││Loader  │
└────────┘└──────┘└──────┘└────────┘
```

---

## manifest 扩展

### 新增字段

在 `manifest.json` 中增加 `extensions` 字段（可选）：

```json
{
  "id": "my-new-mod",
  "name": "我的新模块",
  "version": "1.0.0",
  "artifact": "mod",
  "backend": {
    "entry": "blueprints",
    "init": "mod_init"
  },
  "extensions": {
    "middleware": [
      {
        "file": "backend/middleware.py",
        "factory": "create_auth_middleware",
        "order": 10
      }
    ],
    "background_tasks": [
      {
        "file": "backend/tasks.py",
        "function": "cleanup_expired_orders",
        "schedule": "0 * * * *"
      }
    ],
    "db_migrations": [
      {
        "version": "001",
        "file": "migrations/001_add_tables.sql",
        "description": "创建订单扩展表"
      }
    ],
    "event_subscriptions": {
      "order.created": "backend/handlers.py:on_order_created",
      "payment.completed": "backend/handlers.py:on_payment_completed"
    },
    "service_overrides": {
      "get_products_service": "backend/overrides.py:get_custom_products"
    },
    "frontend_plugins": [
      {
        "type": "global_component",
        "entry": "frontend/plugins/GlobalToolbar.vue",
        "mount_point": "app-header"
      }
    ]
  }
}
```

### 扩展类型说明

| 类型 | 说明 | 加载时机 |
|------|------|----------|
| `middleware` | 中间件（鉴权、限流、日志等） | 路由注册前 |
| `background_tasks` | 定时/后台任务 | 应用启动后 |
| `db_migrations` | 数据库迁移 | 应用初始化时 |
| `event_subscriptions` | 事件订阅 | 路由注册前 |
| `service_overrides` | 服务覆盖/替换 | 应用初始化时 |
| `frontend_plugins` | 前端插件组件 | 前端加载时（声明式） |

---

## 主系统实现

### 1. 扩展加载器基类

```python
# app/infrastructure/mods/extension_loader.py

from abc import ABC, abstractmethod
from typing import Any, Dict, List

from .manifest import ModMetadata

class ExtensionLoader(ABC):
    """扩展加载器基类，每种扩展类型实现一个子类"""
    
    @property
    @abstractmethod
    def extension_type(self) -> str:
        """返回支持的扩展类型名，如 'middleware'"""
        pass
    
    @abstractmethod
    def load(self, mod_id: str, extension_config: List[Dict[str, Any]], mod_path: str) -> bool:
        """
        加载指定类型的扩展
        
        Args:
            mod_id: MOD ID
            extension_config: manifest.extensions[type] 的配置列表/对象
            mod_path: MOD 物理路径
        
        Returns:
            是否加载成功
        """
        pass
    
    @abstractmethod
    def unload(self, mod_id: str) -> bool:
        """卸载扩展（可选，返回 False 表示不支持卸载）"""
        pass
```

### 2. 扩展加载器管理器

```python
# app/infrastructure/mods/extension_manager.py

import logging
from typing import Dict, List, Type

from .extension_loader import ExtensionLoader
from .manifest import ModMetadata

logger = logging.getLogger(__name__)

class ExtensionManager:
    _instance = None
    _loaders: Dict[str, ExtensionLoader] = {}
    
    @classmethod
    def get_instance(cls) -> "ExtensionManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def register_loader(self, loader: ExtensionLoader):
        """注册一个新的扩展加载器"""
        self._loaders[loader.extension_type] = loader
        logger.info("Extension loader registered: %s", loader.extension_type)
    
    def load_extensions(self, mod_id: str, metadata: ModMetadata, mod_path: str) -> Dict[str, bool]:
        """
        加载 MOD 声明的所有扩展
        
        Returns:
            {扩展类型: 是否成功}
        """
        extensions = getattr(metadata, 'extensions', {}) or {}
        results = {}
        
        for ext_type, config in extensions.items():
            loader = self._loaders.get(ext_type)
            if not loader:
                logger.warning("No loader for extension type '%s' (mod: %s)", ext_type, mod_id)
                results[ext_type] = False
                continue
            
            try:
                ok = loader.load(mod_id, config, mod_path)
                results[ext_type] = ok
                logger.info("Extension loaded: mod=%s, type=%s, ok=%s", mod_id, ext_type, ok)
            except Exception as e:
                logger.error("Extension load failed: mod=%s, type=%s, error=%s", mod_id, ext_type, e)
                results[ext_type] = False
        
        return results
    
    def unload_extensions(self, mod_id: str) -> Dict[str, bool]:
        """卸载 MOD 的所有扩展"""
        results = {}
        for ext_type, loader in self._loaders.items():
            try:
                ok = loader.unload(mod_id)
                results[ext_type] = ok
            except Exception as e:
                logger.error("Extension unload failed: mod=%s, type=%s, error=%s", mod_id, ext_type, e)
                results[ext_type] = False
        return results


def get_extension_manager() -> ExtensionManager:
    return ExtensionManager.get_instance()
```

### 3. 内置加载器示例

#### 中间件加载器

```python
# app/infrastructure/mods/loaders/middleware_loader.py

from typing import Any, Dict, List
import importlib

from ..extension_loader import ExtensionLoader

_registered_middlewares = []

class MiddlewareLoader(ExtensionLoader):
    @property
    def extension_type(self) -> str:
        return "middleware"
    
    def load(self, mod_id: str, extension_config: List[Dict[str, Any]], mod_path: str) -> bool:
        for item in extension_config:
            file_path = item.get("file", "")
            factory_fn = item.get("factory", "")
            order = item.get("order", 100)
            
            # 导入模块
            module = self._import_backend_module(file_path, mod_id, mod_path)
            factory = getattr(module, factory_fn, None)
            
            if callable(factory):
                middleware = factory()
                _registered_middlewares.append({
                    "mod_id": mod_id,
                    "middleware": middleware,
                    "order": order
                })
        
        return True
    
    def unload(self, mod_id: str) -> bool:
        global _registered_middlewares
        _registered_middlewares = [m for m in _registered_middlewares if m["mod_id"] != mod_id]
        return True
    
    def _import_backend_module(self, file_path: str, mod_id: str, mod_path: str):
        # 复用 mod_manager.import_mod_backend_py 逻辑
        pass
```

#### 事件订阅加载器

```python
# app/infrastructure/mods/loaders/event_loader.py

from typing import Any, Dict, List
import importlib

from ..extension_loader import ExtensionLoader
from app.infrastructure.mods.hooks import subscribe

class EventLoader(ExtensionLoader):
    @property
    def extension_type(self) -> str:
        return "event_subscriptions"
    
    def load(self, mod_id: str, extension_config: Dict[str, str], mod_path: str) -> bool:
        for event_name, handler_spec in extension_config.items():
            module_name, _, attr_name = handler_spec.rpartition(".")
            # 导入并订阅
            # ...
            subscribe(event_name, handler)
        return True
    
    def unload(self, mod_id: str) -> bool:
        # 事件系统需要跟踪订阅者来源才能卸载
        return False
```

#### 后台任务加载器

```python
# app/infrastructure/mods/loaders/task_loader.py

from typing import Any, Dict, List
from apscheduler.schedulers.background import BackgroundScheduler

from ..extension_loader import ExtensionLoader

class BackgroundTaskLoader(ExtensionLoader):
    @property
    def extension_type(self) -> str:
        return "background_tasks"
    
    def load(self, mod_id: str, extension_config: List[Dict[str, Any]], mod_path: str) -> bool:
        scheduler = BackgroundScheduler()
        
        for item in extension_config:
            file_path = item.get("file", "")
            function = item.get("function", "")
            schedule = item.get("schedule", "")  # cron 表达式
            
            fn = self._import_function(file_path, function, mod_id, mod_path)
            scheduler.add_job(fn, 'cron', cron_expr=schedule, id=f"{mod_id}_{function}")
        
        scheduler.start()
        return True
    
    def unload(self, mod_id: str) -> bool:
        # 移除该 mod 的所有任务
        return True
```

### 4. 集成到 ModManager

```python
# app/infrastructure/mods/mod_manager.py (修改部分)

class ModManager:
    def __init__(self, mods_root: Optional[str] = None):
        # ... 原有代码 ...
        from .extension_manager import get_extension_manager
        self.extension_manager = get_extension_manager()
        self._register_builtin_loaders()
    
    def _register_builtin_loaders(self):
        """注册内置扩展加载器"""
        from .loaders.middleware_loader import MiddlewareLoader
        from .loaders.event_loader import EventLoader
        from .loaders.task_loader import BackgroundTaskLoader
        # ...
        
        self.extension_manager.register_loader(MiddlewareLoader())
        self.extension_manager.register_loader(EventLoader())
        self.extension_manager.register_loader(BackgroundTaskLoader())
        # ...
    
    def load_mod(self, mod_id: str) -> bool:
        # ... 原有加载逻辑 ...
        
        # 加载扩展
        if metadata:
            ext_results = self.extension_manager.load_extensions(mod_id, metadata, mod_path)
            logger.info("Mod %s extensions loaded: %s", mod_id, ext_results)
        
        return True
    
    def unload_mod(self, mod_id: str) -> bool:
        # 卸载扩展
        self.extension_manager.unload_extensions(mod_id)
        # ... 原有卸载逻辑 ...
```

---

## 集成步骤

1. **创建文件**
   - `app/infrastructure/mods/extension_loader.py` — 基类
   - `app/infrastructure/mods/extension_manager.py` — 管理器
   - `app/infrastructure/mods/loaders/` — 各类型加载器

2. **修改 ModMetadata**
   - 在 `app/infrastructure/mods/manifest.py` 的 `ModMetadata` 中增加 `extensions` 字段

3. **修改 ModManager**
   - 在 `load_mod()` 后调用 `extension_manager.load_extensions()`
   - 在 `unload_mod()` 前调用 `extension_manager.unload_extensions()`

4. **注册内置加载器**
   - 至少实现 `middleware`、`event_subscriptions`、`background_tasks`

5. **测试**
   - 创建一个测试 MOD，声明扩展
   - 验证加载/卸载流程

---

## 加载优先级

```
应用启动
  │
  ├── 1. db_migrations        ← 数据库最先
  ├── 2. service_overrides    ← 服务替换
  ├── 3. middleware            ← 中间件注册
  ├── 4. event_subscriptions   ← 事件订阅
  ├── 5. backend.init()        ← 原有 MOD 初始化
  ├── 6. register_fastapi_routes  ← 路由注册
  └── 7. background_tasks      ← 最后启动后台任务
```

---

## MOD 开发示例

假设要创建一个"短信通知"MOD：

```json
{
  "id": "sms-notify",
  "name": "短信通知模块",
  "version": "1.0.0",
  "extensions": {
    "event_subscriptions": {
      "order.created": "backend/handlers.py:notify_on_order",
      "order.shipped": "backend/handlers.py:notify_on_ship"
    },
    "background_tasks": [
      {
        "file": "backend/tasks.py",
        "function": "retry_failed_sends",
        "schedule": "*/5 * * * *"
      }
    ]
  }
}
```

```python
# backend/handlers.py
def notify_on_order(order_data):
    """订单创建时发送短信"""
    # 调用短信 API...
    pass
```

```python
# backend/tasks.py
def retry_failed_sends():
    """每 5 分钟重试失败的短信"""
    # 查询失败记录并重试...
    pass
```

---

## 未来扩展示例

如果以后需要新的扩展类型（如 WebSocket 中间件、缓存策略），只需要：

1. 新增一个 `XXXLoader` 类继承 `ExtensionLoader`
2. 在 `_register_builtin_loaders()` 中注册
3. MOD 在 manifest 中声明即可

**主系统和 MOD 之间形成真正的"插件生态"。**

---

## 远端 Mod Catalog 接入

FHD 内置的 `/api/mod-store/*` 兼容接口可作为修茈公网 Catalog 的服务端代理使用，前端仍访问本机后端，后端再读取远端 `/v1`。

### 环境变量

```env
XCAGI_CATALOG_BASE_URL=https://xiu-ci.com/v1
XCAGI_CATALOG_TOKEN=
VITE_MARKET_BASE=https://xiu-ci.com/market
```

- `XCAGI_CATALOG_BASE_URL`：远端 Catalog 根地址，必须指向暴露 `/index.json`、`/packages/{id}/{version}/download` 的 `/v1` 服务。
- `XCAGI_CATALOG_TOKEN`：只读列表与下载默认留空；若修茈侧开启鉴权，填写 Bearer token。
- `VITE_MARKET_BASE`：前端卡片「网页查看」链接基址，不参与安装下载。

### 接入检查

1. 先确认公网可访问：`curl https://xiu-ci.com/v1/index.json`。
2. 再确认本机代理：`curl http://127.0.0.1:5000/api/mod-store/catalog`。
3. 安装失败且返回 502 时，优先检查修茈 Nginx 是否已将 `/v1/` 反代到 `modstore_server`。
4. 安装成功后，用 `/api/mods/loading-status` 查看 `discovered_mod_ids` 与 `load_errors`。

---

## 修茈市场账号同步

「模型支付」页提供 **修茈账号同步**：本机后端 `POST /api/market/account-sync` 携带用户粘贴的 `Authorization`，代请求修茈 `{XCAGI_MARKET_BASE_URL}/api/auth/me`，返回脱敏后的用户档案；前端将令牌与档案写入 `localStorage`（`xcagi_market_access_token` / `xcagi_market_user_json`），便于后续功能携带同一修茈身份。

### 环境变量

```env
XCAGI_MARKET_BASE_URL=https://xiu-ci.com
```

### 安全说明

- 令牌**不落盘**到服务端配置；仅本次请求转发到修茈 HTTPS。
- 浏览器 `localStorage` 存 token 有 XSS 风险，请勿在不可信环境粘贴长期令牌。
