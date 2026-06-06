"""
``app.mod_sdk`` — XCAGI Mod 面向主程的唯一稳定 API 面。

背景
----

每个 Mod 是独立文件夹（见 ``mods/<id>/manifest.json``）。
在 2026-04-20 的 Neuro-DDD 重整之前，Mod 代码可以随意 ``from app.<内部模块> import ...``。
这带来两个问题：

1.  主程一重构，Mod 就炸（``app.routes.*`` 变 ``app.fastapi_routes.*`` 就是例子）。
2.  "每个 Mod 一个文件夹"的独立性空心化：物理目录隔离，但依赖图与主程深度耦合。

``app.mod_sdk`` 是主程对 Mod 承诺的**稳定契约层**：

- Mod 代码**只允许** ``from app.mod_sdk.<submodule> import ...``。
  其它任何 ``app.*`` 前缀（如 ``app.services.*``、``app.db.*``、``app.routes.*``、``app.application.*``、
  ``app.bootstrap``）都**不再**对 Mod 可见。
- 每次主程内部重构，只需要保证 ``app.mod_sdk.*`` 的符号不变即可，Mod 就不会因内部搬家而挂。
- 约束由 ``scripts/dev/check_mod_import_boundaries.py`` 强制检查，CI 与冒烟脚本里都会跑。

子模块分布
----------

+-----------------------+--------------------------------------------------------+
| 子模块                | 提供                                                    |
+=======================+========================================================+
| ``mod_sdk.comms``     | Mod 间消息总线：``register`` / ``call`` /              |
|                       | ``get_caller_mod_id`` / ``get_mod_comms``              |
+-----------------------+--------------------------------------------------------+
| ``mod_sdk.mods_bus``  | 跨 Mod 动态加载同 Mod 内 ``backend/*.py``：            |
|                       | ``import_mod_backend_py``                              |
+-----------------------+--------------------------------------------------------+
| ``mod_sdk.db``        | SQLAlchemy 会话工厂 ``SessionLocal``                    |
+-----------------------+--------------------------------------------------------+
| ``mod_sdk.db_models`` | 受限 ORM 模型直通（``PurchaseUnit`` 等）；              |
|                       | 新代码尽量走 ``mod_sdk.services`` 高层方法。           |
+-----------------------+--------------------------------------------------------+
| ``mod_sdk.services``  | 主程高层服务：``get_products_service`` /                |
|                       | ``get_ai_chat_app_service`` /                          |
|                       | ``get_unified_intent_recognizer``                      |
+-----------------------+--------------------------------------------------------+
| ``mod_sdk.tts``       | 语音合成：``synthesize_to_data_uri``                    |
+-----------------------+--------------------------------------------------------+
| ``mod_sdk.state``     | 运行时客户端开关：``read_client_mods_off_state``        |
+-----------------------+--------------------------------------------------------+
| ``mod_sdk.ai_helpers``| 数值/金额格式化：``safe_float`` / ``format_money``      |
+-----------------------+--------------------------------------------------------+
| ``mod_sdk.workspace`` | 工作区相对路径安全解析：                                  |
|                       | ``resolve_safe_workspace_relpath``                     |
+-----------------------+--------------------------------------------------------+
| ``mod_sdk.private_sqlite`` | Mod 自有 SQLite 路径 ``resolve_mod_private_sqlite_path`` |
|                       |（与主库 ``data/`` 及桌面 ``DATABASE_PATH`` 对齐）       |
+-----------------------+--------------------------------------------------------+
| ``mod_sdk.attendance``| 考勤转换（太阳鸟 PRO 依赖）；                            |
|                       | 未来任务 B 会把该能力下沉回 ``mods/taiyangniao-pro/``   |
|                       | 后本文件会收窄为空或移除。                               |
+-----------------------+--------------------------------------------------------+
| ``mod_sdk.mod_employee_llm`` | Mod 员工窄 LLM：``mod_employee_complete``（生成物     |
|                       | ``blueprints._call_llm`` 优先调用，走宿主对话配置）     |
+-----------------------+--------------------------------------------------------+
"""

from __future__ import annotations

from app.mod_sdk import (  # noqa: F401
    ai_helpers,
    attendance,
    audit,
    comms,
    db,
    db_models,
    mod_employee_llm,
    mods_bus,
    private_sqlite,
    services,
    state,
    tts,
    workspace,
)

__all__ = [
    "ai_helpers",
    "attendance",
    "audit",
    "comms",
    "db",
    "db_models",
    "mod_employee_llm",
    "mods_bus",
    "private_sqlite",
    "services",
    "state",
    "tts",
    "workspace",
]
