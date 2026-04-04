from app.db.models.ai import (
    AIConversation,
    AIConversationSession,
    AITool,
    AIToolCategory,
    UserPreference,
)
from app.db.models.customer import Customer
from app.db.models.inventory import (
    InventoryLedger,
    InventoryTransaction,
    StorageLocation,
    Warehouse,
)
from app.db.models.material import Material
from app.db.models.miniprogram import (
    MpAddress,
    MpBrowseHistory,
    MpCart,
    MpFavorite,
    MpFeedback,
    MpNotification,
    MpOrder,
    MpOrderItem,
)
from app.db.models.permission import Permission, Role, role_permissions
from app.db.models.product import Product
from app.db.models.purchase import (
    PurchaseInbound,
    PurchaseInboundItem,
    PurchaseOrder,
    PurchaseOrderItem,
    Supplier,
)
from app.db.models.purchase_unit import PurchaseUnit
from app.db.models.shipment import ShipmentRecord
from app.db.models.user import Session as UserSession
from app.db.models.user import User
from app.db.models.wechat import WechatContact, WechatContactContext, WechatTask

__all__ = [
    "PurchaseUnit",
    "Product",
    "ShipmentRecord",
    "Customer",
    "WechatTask",
    "WechatContact",
    "WechatContactContext",
    "User",
    "UserSession",
    "Permission",
    "Role",
    "AIToolCategory",
    "AITool",
    "AIConversation",
    "AIConversationSession",
    "UserPreference",
    "Material",
    "Warehouse",
    "StorageLocation",
    "InventoryLedger",
    "InventoryTransaction",
    "Supplier",
    "PurchaseOrder",
    "PurchaseOrderItem",
    "PurchaseInbound",
    "PurchaseInboundItem",
    "MpCart",
    "MpOrder",
    "MpOrderItem",
    "MpAddress",
    "MpBrowseHistory",
    "MpFavorite",
    "MpNotification",
    "MpFeedback",
]
