"""
AppService V1 / V2 成对登记与 HTTP 层选型说明。

V2 模块多为 NeuroBus 事件驱动入口（execute_command / publish），与 FastAPI/legacy
路由直接调用的 V1 同步 API（login、get_session_messages 等）**签名不一致**。
在 V2 补齐同等 HTTP 契约前，路由与 planner 工具链应继续使用 V1 getter。

本模块供架构巡检与迁移脚本引用；新增 *_app_service_v2 时请同步更新 APP_SERVICE_PAIRS。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

HttpLayer = Literal["v1", "v2"]


@dataclass(frozen=True)
class AppServicePair:
    """单个业务域的 V1/V2 文件与 HTTP 推荐层。"""

    domain: str
    v1_module: str
    v1_getter: str
    v2_module: str
    v2_getter: str
    http_layer: HttpLayer
    notes: str


APP_SERVICE_PAIRS: tuple[AppServicePair, ...] = (
    AppServicePair(
        "auth",
        "auth_app_service",
        "get_auth_app_service",
        "auth_app_service_v2",
        "get_auth_app_service_v2",
        "v1",
        "V2 仅 execute_command；legacy_auth 需 login/session_manager。",
    ),
    AppServicePair(
        "user",
        "user_app_service",
        "get_user_app_service",
        "user_app_service_v2",
        "get_user_app_service_v2",
        "v1",
        "V2 为事件命令入口；用户 CRUD 仍在 V1。",
    ),
    AppServicePair(
        "customer",
        "customer_app_service",
        "get_customer_app_service",
        "customer_app_service_v2",
        "get_customer_app_service_v2",
        "v1",
        "HTTP 与 planner 大量调用 V1 CustomerApplicationService。",
    ),
    AppServicePair(
        "conversation",
        "conversation_app_service",
        "get_conversation_app_service",
        "conversation_app_service_v2",
        "get_conversation_app_service_v2",
        "v1",
        "legacy_conversation 依赖 save_message/get_session_messages。",
    ),
    AppServicePair(
        "shipment",
        "shipment_app_service",
        "get_shipment_application_service",
        "shipment_app_service_v2",
        "get_shipment_app_service_v2",
        "v1",
        "miniprogram 使用 query_shipment_orders/get_order；V2 为异步事件 API。",
    ),
    AppServicePair(
        "template",
        "template_app_service",
        "get_template_app_service",
        "template_app_service_v2",
        "get_template_app_service_v2",
        "v1",
        "模板分解与文件读写仍在 V1。",
    ),
    AppServicePair(
        "wechat_contact",
        "wechat_contact_app_service",
        "get_wechat_contact_app_service",
        "wechat_contact_app_service_v2",
        "get_wechat_contact_app_service_v2",
        "v1",
        "legacy_wechat 同步联系人接口。",
    ),
    AppServicePair(
        "wechat_task",
        "wechat_task_app_service",
        "get_wechat_task_app_service",
        "wechat_task_app_service_v2",
        "get_wechat_task_app_service_v2",
        "v1",
        "任务确认/忽略等仍在 V1。",
    ),
    AppServicePair(
        "ai_chat",
        "ai_chat_app_service",
        "get_ai_chat_app_service",
        "ai_chat_app_service_v2",
        "get_ai_chat_app_service_v2",
        "v1",
        "主对话与工具编排体量在 V1；V2 为侧车事件入口。",
    ),
    AppServicePair(
        "product",
        "product_app_service",
        "get_product_app_service",
        "product_app_service_v2",
        "get_product_app_service_v2",
        "v1",
        "",
    ),
    AppServicePair(
        "material",
        "material_app_service",
        "get_material_app_service",
        "material_app_service_v2",
        "get_material_app_service_v2",
        "v1",
        "",
    ),
    AppServicePair(
        "print",
        "print_app_service",
        "get_print_application_service",
        "print_app_service_v2",
        "get_print_app_service_v2",
        "v1",
        "路由使用 get_print_application_service。",
    ),
    AppServicePair(
        "ocr",
        "ocr_app_service",
        "get_ocr_application_service",
        "ocr_app_service_v2",
        "get_ocr_app_service_v2",
        "v1",
        "",
    ),
    AppServicePair(
        "excel_vector",
        "excel_vector_app_service",
        "get_excel_vector_ingest_app_service",
        "excel_vector_app_service_v2",
        "get_excel_vector_app_service_v2",
        "v1",
        "ingest/search 仍走 V1 类；V2 为命令入口。",
    ),
    AppServicePair(
        "file_analysis",
        "file_analysis_app_service",
        "get_file_analysis_app_service",
        "file_analysis_app_service_v2",
        "get_file_analysis_app_service_v2",
        "v1",
        "legacy_excel 使用 V1。",
    ),
    AppServicePair(
        "unit_products_import",
        "unit_products_import_app_service",
        "get_unit_products_import_app_service",
        "unit_products_import_app_service_v2",
        "get_unit_products_import_app_service_v2",
        "v1",
        "",
    ),
    AppServicePair(
        "product_import",
        "product_import_app_service",
        "get_product_import_application_service",
        "product_import_app_service_v2",
        "get_product_import_app_service_v2",
        "v1",
        "",
    ),
    AppServicePair(
        "extract_log",
        "extract_log_app_service",
        "get_extract_log_app_service",
        "extract_log_app_service_v2",
        "get_extract_log_app_service_v2",
        "v1",
        "",
    ),
    AppServicePair(
        "user_preference",
        "user_preference_app_service",
        "get_user_preference_app_service",
        "user_preference_app_service_v2",
        "get_user_preference_app_service_v2",
        "v1",
        "",
    ),
    AppServicePair(
        "user_memory_vector",
        "user_memory_vector_app_service",
        "get_user_memory_vector_ingest_app_service / get_user_memory_rag_app_service",
        "user_memory_vector_app_service_v2",
        "get_user_memory_vector_app_service_v2",
        "v1",
        "ingest/rag 在 V1；V2 单例为事件侧入口。",
    ),
)


def iter_pairs() -> tuple[AppServicePair, ...]:
    return APP_SERVICE_PAIRS


def domains_on_v1_http() -> tuple[str, ...]:
    return tuple(p.domain for p in APP_SERVICE_PAIRS if p.http_layer == "v1")
