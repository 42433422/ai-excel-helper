"""受限 ORM 模型直通（SDK re-export）。

警告
----

这里暴露的是**具体 ORM 类**，耦合度高：字段改名 / 主键变化会直接波及 Mod。
**只在没有对应高层服务**（``mod_sdk.services``）时才使用。未来如果
``products_service`` / 其它 Application Service 补全了等价查询方法，
本模块会把对应模型标记为 ``DeprecationWarning``。
"""

from __future__ import annotations

from app.db.models import PurchaseUnit  # noqa: F401

__all__ = ["PurchaseUnit"]
