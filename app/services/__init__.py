"""
服务层模块

提供业务逻辑服务，包括：
- 意图识别服务
- AI 对话服务
- 客户管理服务
- 产品管理服务
- 发货单服务
- 微信服务

注意：此模块已完全迁移到 DDD 分层架构。
- 工具服务在 app/utils/
- 基础设施在 app/infrastructure/
- 应用服务在 app/application/
- AI 引擎在 app/ai_engines/
- 领域服务在 app/domain/services/

此文件保留为统一导出入口。
"""

from app.ai_engines.bert.intent_service import BertIntentClassifier
from app.ai_engines.deepseek.intent_service import DeepseekIntentClassifier
from app.ai_engines.rasa.nlu_service import RasaNLUService, get_rasa_nlu_service
from app.domain.services.intent_confirmation_service import (
    IntentConfirmationService,
    get_confirmation_service,
)
from app.domain.services.unified_intent_recognizer import (
    UnifiedIntentRecognizer,
    get_unified_intent_recognizer,
)
from app.infrastructure.session.session_manager import SessionManager, get_session_manager
from app.services.ai_conversation_service import (
    AIConversationService,
    get_ai_conversation_service,
    init_ai_conversation_service,
)
from app.services.auth_service import AuthService, get_auth_service
from app.services.extract_log_service import ExtractLogService
from app.services.hybrid_intent_service import (
    HybridIntentService,
    get_hybrid_intent_service,
    hybrid_recognize_intents,
    hybrid_recognize_intents_sync,
)
from app.services.intent_service import get_tool_key_with_negation_check, recognize_intents
from app.services.materials_service import MaterialsService
from app.services.ocr_service import OCRService, get_ocr_service
from app.services.printer_service import (
    PrinterService,
    get_document_printer,
    get_label_printer,
    get_printers,
)
from app.services.product_import_service import ProductImportService
from app.services.products_service import ProductsService
from app.services.task_agent import TaskAgent, get_task_agent
from app.services.user_service import UserService, get_user_service
from app.services.wechat_task_service import WechatTaskService
from app.utils.database_service import get_database_service
from app.utils.system_service import get_system_service
from app.utils.task_context import TaskContextService, get_task_context_service
from app.utils.user_memory import UserMemoryService, get_user_memory_service


def get_wechat_task_service() -> WechatTaskService:
    """获取微信任务服务单例"""
    return WechatTaskService()

from app.services.ai_product_parser import AIProductParser
from app.services.conversation_service import ConversationService, get_conversation_service
from app.services.session_service import SessionService, get_session_service
from app.services.system_service import SystemService, get_system_service
from app.services.tts_service import synthesize_to_data_uri
from app.services.user_preference_service import UserPreferenceService, get_user_preference_service


def get_ai_product_parser() -> AIProductParser:
    """获取 AI 产品解析器单例"""
    return AIProductParser()

from app.infrastructure.skills import execute_skill, get_skill_registry


def get_products_service() -> ProductsService:
    """获取产品服务单例"""
    return ProductsService()


def get_printer_service() -> PrinterService:
    """获取打印机服务单例"""
    return PrinterService()


def get_materials_service() -> MaterialsService:
    """获取材质服务单例"""
    return MaterialsService()


def get_product_import_service() -> ProductImportService:
    """获取产品导入服务单例"""
    return ProductImportService()


def get_extract_log_service() -> ExtractLogService:
    """获取提取日志服务单例"""
    return ExtractLogService()

__all__ = [
    "recognize_intents",
    "get_tool_key_with_negation_check",
    "RasaNLUService",
    "get_rasa_nlu_service",
    "HybridIntentService",
    "get_hybrid_intent_service",
    "hybrid_recognize_intents",
    "hybrid_recognize_intents_sync",
    "get_ai_conversation_service",
    "init_ai_conversation_service",
    "AIConversationService",
    "get_task_agent",
    "TaskAgent",
    "get_task_context_service",
    "TaskContextService",
    "get_database_service",
    "get_system_service",
    "get_user_memory_service",
    "UserMemoryService",
    "ProductImportService",
    "get_product_import_service",
    "ExtractLogService",
    "get_extract_log_service",
    "IntentConfirmationService",
    "get_confirmation_service",
    "UnifiedIntentRecognizer",
    "get_unified_intent_recognizer",
    "BertIntentClassifier",
    "DeepseekIntentClassifier",
    "SessionManager",
    "get_session_manager",
    "ProductsService",
    "get_products_service",
    "PrinterService",
    "get_printer_service",
    "get_label_printer",
    "get_document_printer",
    "get_printers",
    "OCRService",
    "get_ocr_service",
    "MaterialsService",
    "get_materials_service",
    "UserService",
    "get_user_service",
    "AuthService",
    "get_auth_service",
    "WechatTaskService",
    "get_wechat_task_service",
    "ConversationService",
    "get_conversation_service",
    "SessionService",
    "get_session_service",
    "SystemService",
    "get_system_service",
    "UserPreferenceService",
    "get_user_preference_service",
    "AIProductParser",
    "get_ai_product_parser",
    "get_skill_registry",
    "execute_skill",
    "synthesize_to_data_uri",
]
