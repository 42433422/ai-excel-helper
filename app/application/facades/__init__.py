"""
NeuroDDD 域门面层

域门面（Domain Facade）是 NeuroDDD 架构中路由层与领域层的桥接层。
与传统 DDD 的 Facade 不同，NeuroDDD 域门面：
- 变更操作通过 NeuroBus 发布领域事件
- 查询操作直接委托给领域服务（Conscious Processor 同步调用模式）
- 跨域操作通过 CommandGateway 实现请求-回复

参考：shipment_event_primary.py 是完整的 CommandGateway 模式范例。
"""

from app.application.facades.ai_conversation_facade import AIConversationService
from app.application.facades.conversation_facade import (
    get_conversation_service,
    get_data_analysis_service,
    get_user_preference_service,
)
from app.application.facades.excel_facade import get_ai_product_parser, get_product_import_service
from app.application.facades.intent_facade import BertIntentClassifier
from app.application.facades.inventory_facade import (
    InventoryService,
    PurchaseService,
    ReportService,
)
from app.application.facades.kitten_facade import (
    KittenReportExportService,
    analysis_save_service,
    build_kitten_business_snapshot,
    build_kitten_docx,
    chart_service,
    generate_office_file,
    pop_document_pickup,
    FinancialReportPlugin,
    InventoryValuationPlugin,
)
from app.application.facades.ocr_facade import get_ocr_service
from app.application.facades.print_facade import printer_service
from app.application.facades.query_facade import (
    find_product,
    find_purchase_unit,
    get_product_names,
    get_purchase_units,
    query_service,
)
from app.application.facades.session_facade import (
    get_auth_service,
    get_database_service,
    get_session_service,
    get_system_service,
)
from app.application.facades.shipment_event_primary import (
    ShipmentApplicationServiceEventPrimary,
)
from app.application.facades.template_facade import (
    _extract_structured_excel_preview,
    document_templates_service,
)
from app.application.facades.tools_facade import (
    _parse_order_text,
    execute_registered_workflow_tool,
    execute_tool_from_payload,
    get_workflow_tool_registry,
    set_tool_execute_headers,
)
from app.application.facades.tts_facade import synthesize_to_data_uri, trigger_common_tts_warmup
from app.application.facades.wechat_facade import (
    WechatMiniProgramError,
    get_wechat_config,
    miniprogram_login_data_for_wx_username_binding,
    refresh_wechat_contacts_from_decrypt,
    wechat_login_code2session,
    wechat_message_source_size_payload,
)

__all__ = [
    "ShipmentApplicationServiceEventPrimary",
    "AIConversationService",
    "BertIntentClassifier",
    "InventoryService",
    "PurchaseService",
    "ReportService",
    "KittenReportExportService",
    "FinancialReportPlugin",
    "InventoryValuationPlugin",
    "WechatMiniProgramError",
    "document_templates_service",
    "_extract_structured_excel_preview",
    "_parse_order_text",
    "execute_registered_workflow_tool",
    "execute_tool_from_payload",
    "get_workflow_tool_registry",
    "set_tool_execute_headers",
    "build_kitten_business_snapshot",
    "build_kitten_docx",
    "chart_service",
    "analysis_save_service",
    "generate_office_file",
    "pop_document_pickup",
    "find_product",
    "find_purchase_unit",
    "get_product_names",
    "get_purchase_units",
    "query_service",
    "get_conversation_service",
    "get_data_analysis_service",
    "get_user_preference_service",
    "get_ai_product_parser",
    "get_product_import_service",
    "get_auth_service",
    "get_database_service",
    "get_session_service",
    "get_system_service",
    "get_ocr_service",
    "get_wechat_config",
    "get_wechat_config",
    "miniprogram_login_data_for_wx_username_binding",
    "refresh_wechat_contacts_from_decrypt",
    "wechat_login_code2session",
    "wechat_message_source_size_payload",
    "printer_service",
    "synthesize_to_data_uri",
    "trigger_common_tts_warmup",
]
