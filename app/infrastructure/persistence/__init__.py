from app.infrastructure.persistence.material_repository_impl import SQLAlchemyMaterialRepository
from app.infrastructure.persistence.product_repository_impl import SQLAlchemyProductRepository
from app.infrastructure.persistence.shipment_record_store_impl import SQLAlchemyShipmentRecordStore
from app.infrastructure.persistence.wechat_contact_store_impl import SQLAlchemyWechatContactStore

__all__ = [
    "SQLAlchemyShipmentRecordStore",
    "SQLAlchemyWechatContactStore",
    "SQLAlchemyMaterialRepository",
    "SQLAlchemyProductRepository",
]

