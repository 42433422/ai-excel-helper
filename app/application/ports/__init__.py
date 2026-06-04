"""
NeuroDDD 域通道接口

域通道（Domain Channel）是 NeuroDDD 架构中领域层与基础设施层的契约接口。
与传统 DDD 的 Port 不同，NeuroDDD 域通道：
- 定义领域与基础设施的通信契约
- 由 NeuroDomain 的处理器通过 DomainChannel 调用
- 基础设施实现注册到 NeuroBus 的领域处理器中

命名映射（向后兼容）：
- Port → Channel（语义对齐 NeuroDDD 的 DomainChannel）
- Repository → Channel（数据访问通道）
"""

from app.application.ports.embedder import EmbedderPort as EmbedderChannel
from app.application.ports.extract_log_store import ExtractLogStorePort as ExtractLogStoreChannel
from app.application.ports.file_analysis import FileAnalysisPort as FileAnalysisChannel
from app.application.ports.material_repository import MaterialRepository as MaterialChannel
from app.application.ports.product_repository import ProductRepository as ProductChannel
from app.application.ports.purchase_unit_query import (
    PurchaseUnitQueryPort as PurchaseUnitQueryChannel,
)
from app.application.ports.shipment_document_generator import (
    ShipmentDocumentGeneratorPort as ShipmentDocumentGeneratorChannel,
)
from app.application.ports.shipment_record_command import (
    ShipmentRecordCommandPort as ShipmentRecordCommandChannel,
)
from app.application.ports.shipment_record_query import (
    ShipmentRecordQueryPort as ShipmentRecordQueryChannel,
)
from app.application.ports.shipment_record_store import (
    ShipmentRecordStorePort as ShipmentRecordStoreChannel,
)
from app.application.ports.shipment_repository import ShipmentRepository as ShipmentChannel
from app.application.ports.template_store import TemplateStorePort as TemplateStoreChannel
from app.application.ports.vector_store import VectorStorePort as VectorStoreChannel
from app.application.ports.wechat_contact_store import (
    WechatContactStorePort as WechatContactStoreChannel,
)

MaterialRepository = MaterialChannel
ProductRepository = ProductChannel
ShipmentRepository = ShipmentChannel
ShipmentDocumentGeneratorPort = ShipmentDocumentGeneratorChannel
ShipmentRecordCommandPort = ShipmentRecordCommandChannel
ShipmentRecordQueryPort = ShipmentRecordQueryChannel
ShipmentRecordStorePort = ShipmentRecordStoreChannel
PurchaseUnitQueryPort = PurchaseUnitQueryChannel
TemplateStorePort = TemplateStoreChannel
WechatContactStorePort = WechatContactStoreChannel
ExtractLogStorePort = ExtractLogStoreChannel
FileAnalysisPort = FileAnalysisChannel
EmbedderPort = EmbedderChannel
VectorStorePort = VectorStoreChannel

__all__ = [
    "MaterialChannel",
    "ProductChannel",
    "ShipmentChannel",
    "ShipmentDocumentGeneratorChannel",
    "ShipmentRecordCommandChannel",
    "ShipmentRecordQueryChannel",
    "ShipmentRecordStoreChannel",
    "PurchaseUnitQueryChannel",
    "TemplateStoreChannel",
    "WechatContactStoreChannel",
    "ExtractLogStoreChannel",
    "FileAnalysisChannel",
    "EmbedderChannel",
    "VectorStoreChannel",
    "MaterialRepository",
    "ProductRepository",
    "ShipmentRepository",
    "ShipmentDocumentGeneratorPort",
    "ShipmentRecordCommandPort",
    "ShipmentRecordQueryPort",
    "ShipmentRecordStorePort",
    "PurchaseUnitQueryPort",
    "TemplateStorePort",
    "WechatContactStorePort",
    "ExtractLogStorePort",
    "FileAnalysisPort",
    "EmbedderPort",
    "VectorStorePort",
]
