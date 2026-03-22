"""
基础设施层保留的兼容导出：

仓储“接口”属于应用层端口（Port），但历史代码可能仍从
`app.infrastructure.repositories.shipment_repository` 引用它。
"""

from app.application.ports.shipment_repository import ShipmentRepository

__all__ = ["ShipmentRepository"]
