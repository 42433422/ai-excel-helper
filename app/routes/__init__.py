"""
路由蓝图注册模块

注册所有路由蓝图到 Flask 应用。
"""

from flask import Flask
import logging

logger = logging.getLogger(__name__)


def register_blueprints(app: Flask, blueprint_groups: list[str] | None = None) -> None:
    """
    注册所有路由蓝图

    Args:
        app: Flask 应用实例
    """
    from app.control.routes import bp as control_bp

    from .ai_assistant_compat import ai_assistant_compat_bp
    from .ai_chat import ai_chat_bp
    from .ai_parse import ai_parse_bp
    from .ai_analyze import ai_analyze_bp
    from .auth import auth_bp, users_bp
    from .conversations import conversations_bp
    from .customers import customers_bp
    from .distillation import distillation_bp
    from .excel_extract import excel_extract_bp
    from .excel_vector import excel_vector_bp
    from .excel_templates import excel_templates_bp
    from .frontend import frontend_bp
    from .health import health_bp
    from .intent import intent_bp
    from .intent_packages import intent_packages_bp
    from .inventory import inventory_bp
    from .materials import materials_bp
    from .metrics import metrics_bp
    from .ocr import ocr_bp
    from .print import print_bp
    from .products import products_bp
    from .purchase import purchase_bp
    from .report import report_bp
    from .shipment import shipment_bp
    from .skills import skills_bp
    from .system import system_bp
    from .templates import templates_bp
    from .tools import tools_bp
    from .upload import upload_bp
    from .wechat import wechat_bp
    from .wechat_contacts import wechat_contacts_bp
    from .wechat_miniprogram import wechat_miniprogram_bp
    from .miniprogram_api import miniprogram_api_bp

    # ===== 小程序 CRM 模块 (v5) =====
    from .mp_auth import mp_auth_bp
    from .mp_user import mp_user_bp
    from .mp_product import mp_product_bp
    from .mp_cart import mp_cart_bp
    from .mp_order import mp_order_bp
    from .mp_address import mp_address_bp
    from .mp_favorite import mp_favorite_bp
    from .mp_message import mp_message_bp
    from .mp_ai import mp_ai_bp
    from .mp_feedback import mp_feedback_bp

    # 默认分组：两个进程分别承担"材料/基础数据"和"出货/AI 助手/兼容层"。
    groups_map: dict[str, set[str]] = {
        "warehouse": {
            "tools",
            "customers",
            "products",
            "ocr",
            "excel_templates",
            "excel_extract",
            "excel_vector",
            "materials",
            "conversations",
            "distillation",
            "control",
            "health",
            "auth",
            "users",
            "templates",
            "upload",
            "intent",
            "system",  # /api/system/* 行业配置，材料端与设置页共用
        },
        "shipment": {
            "frontend",
            "shipment",
            "wechat",
            "wechat_contacts",
            "ai_chat",
            "distillation",
            "print",
            "ai_assistant_compat",
            "metrics",
            "health",
            "skills",
            "auth",
            "users",
            "templates",
            "upload",
            "intent",
        },
        "all": {
            "frontend",
            "tools",
            "customers",
            "products",
            "purchase",
            "inventory",
            "report",
            "shipment",
            "wechat",
            "wechat_contacts",
            "ai_chat",
            "print",
            "ocr",
            "excel_templates",
            "excel_extract",
            "excel_vector",
            "materials",
            "conversations",
            "distillation",
            "ai_assistant_compat",
            "control",
            "metrics",
            "health",
            "skills",
            "auth",
            "users",
            "templates",
            "upload",
            "intent",
            "intent_packages",
            "system",
        },
    }

    if not blueprint_groups:
        chosen = groups_map["all"]
    else:
        chosen: set[str] = set()
        for g in blueprint_groups:
            chosen |= groups_map.get(g, set())

    if "frontend" in chosen:
        # frontend 最后注册，避免 catch-all 路由覆盖其他 API
        pass  # 稍后处理
    if "tools" in chosen:
        app.register_blueprint(tools_bp)
    if "customers" in chosen:
        app.register_blueprint(customers_bp, url_prefix="/api/customers")
    if "inventory" in chosen:
        app.register_blueprint(inventory_bp, url_prefix="/api/inventory")
    if "products" in chosen:
        app.register_blueprint(products_bp, url_prefix="/api/products")
    if "purchase" in chosen:
        app.register_blueprint(purchase_bp, url_prefix="/api/purchase")
    if "report" in chosen:
        app.register_blueprint(report_bp, url_prefix="/api/report")
    if "shipment" in chosen:
        app.register_blueprint(shipment_bp, url_prefix="/api/shipment")
    if "wechat" in chosen:
        # `wechat_bp` 已在自身 Blueprint 定义了 url_prefix=/api/wechat
        # 此处不要再次传 url_prefix，避免前缀重复导致接口 404
        app.register_blueprint(wechat_bp)
    if "wechat_contacts" in chosen:
        app.register_blueprint(wechat_contacts_bp)  # 兼容旧版前端路径
    if "wechat" in chosen or "miniprogram" in chosen:
        # 注册微信小程序 API
        app.register_blueprint(wechat_miniprogram_bp)
        app.register_blueprint(miniprogram_api_bp)
    if "ai_chat" in chosen:
        # `ai_chat_bp` 已在自身 Blueprint 定义了 url_prefix=/api/ai
        app.register_blueprint(ai_chat_bp)
        # AI 产品解析路由与对话路由共用 /api/ai 前缀
        app.register_blueprint(ai_parse_bp)
        # AI 数据分析路由
        app.register_blueprint(ai_analyze_bp)
    if "print" in chosen:
        # `print_bp` 已在自身 Blueprint 定义了 url_prefix=/api/print
        app.register_blueprint(print_bp)
    if "ocr" in chosen:
        # `ocr_bp` 已在自身 Blueprint 定义了 url_prefix=/api/ocr
        app.register_blueprint(ocr_bp)
    if "excel_templates" in chosen:
        # `excel_templates_bp` 已在自身 Blueprint 定义了 url_prefix=/api/excel
        app.register_blueprint(excel_templates_bp)
    if "excel_extract" in chosen:
        # `excel_extract_bp` 已在自身 Blueprint 定义了 url_prefix=/api/excel/data
        app.register_blueprint(excel_extract_bp)
    if "excel_vector" in chosen:
        # `excel_vector_bp` 已在自身 Blueprint 定义了 url_prefix=/api/excel/vector
        app.register_blueprint(excel_vector_bp)
    if "materials" in chosen:
        app.register_blueprint(materials_bp)
    if "conversations" in chosen:
        app.register_blueprint(conversations_bp)
    if "distillation" in chosen:
        app.register_blueprint(distillation_bp)
    if "control" in chosen:
        app.register_blueprint(control_bp, url_prefix="/api/control")
    if "metrics" in chosen:
        app.register_blueprint(metrics_bp)
    if "health" in chosen:
        app.register_blueprint(health_bp)
    if "skills" in chosen:
        app.register_blueprint(skills_bp)
    # AI助手接口兼容层：不加前缀，直接补齐 /api/* 与 /orders/* 等路径
    if "ai_assistant_compat" in chosen:
        app.register_blueprint(ai_assistant_compat_bp)
    if "auth" in chosen:
        app.register_blueprint(auth_bp)
    if "users" in chosen:
        app.register_blueprint(users_bp)
    if "templates" in chosen or True:  # 始终注册模板路由
        app.register_blueprint(templates_bp)
    if "upload" in chosen or True:  # 始终注册上传路由
        app.register_blueprint(upload_bp)
    if "intent" in chosen:
        app.register_blueprint(intent_bp)
    if "intent_packages" in chosen:
        app.register_blueprint(intent_packages_bp)
    # 行业/系统配置：全分组均注册（原 or True）。warehouse 分组已显式包含 system。
    if "system" in chosen or True:
        app.register_blueprint(system_bp)
    # Mod 系统路由始终注册
    from .mods import bp as mods_bp
    app.register_blueprint(mods_bp)
    logger.info("Mod system API blueprint registered: /api/mods")

    # Client state API (原版模式同步)
    from .state import bp as state_bp
    app.register_blueprint(state_bp)
    logger.info("Client state API blueprint registered: /api/state")

    from app.infrastructure.mods.mod_manager import get_mod_manager, is_mods_disabled, load_mod_blueprints
    from .state import read_client_mods_off_state

    # 检查前端是否启用了原版模式
    client_mods_off = read_client_mods_off_state()
    mod_manager = get_mod_manager()
    if client_mods_off:
        logger.info("[ModManager] 前端已启用原版模式 (client_mods_off=True)：跳过 Mod 插件加载与扩展蓝图注册")
    elif is_mods_disabled():
        logger.info("XCAGI_DISABLE_MODS 已启用：不加载 Mod 插件与扩展蓝图，行业配置使用 resources 内原始 YAML（无 Mod 覆盖）。")
    else:
        loaded_mods = mod_manager.load_all_mods()
        if not loaded_mods:
            logger.error(
                "[ModManager] 未加载任何 Mod。请确认目录存在且可解析：%s；"
                "或设置环境变量 XCAGI_MODS_ROOT（或 XCAGI_MODS_DIR）指向 XCAGI/mods。",
                mod_manager.mods_root,
            )
        if loaded_mods:
            load_mod_blueprints(app, mod_manager)
            logger.info(f"Loaded {len(loaded_mods)} mod(s): {', '.join(loaded_mods)}")

    # frontend 最后注册（catch-all 路由）
    if "frontend" in chosen or True:
        app.register_blueprint(frontend_bp)

    from .traditional_mode import register_traditional_mode_routes
    register_traditional_mode_routes(app)
    logger.info("Traditional mode API blueprint registered: /api/traditional-mode")

    # ===== 注册小程序 CRM API (v5) =====
    app.register_blueprint(mp_auth_bp)
    app.register_blueprint(mp_user_bp)
    app.register_blueprint(mp_product_bp)
    app.register_blueprint(mp_cart_bp)
    app.register_blueprint(mp_order_bp)
    app.register_blueprint(mp_address_bp)
    app.register_blueprint(mp_favorite_bp)
    app.register_blueprint(mp_message_bp)
    app.register_blueprint(mp_ai_bp)
    app.register_blueprint(mp_feedback_bp)
    logger.info("MiniProgram CRM API blueprints registered: /api/mp/v1/*")

    # ===== 注册性能优化与监控 API (v4 Performance) =====
    try:
        from .performance import register_performance_blueprint
        register_performance_blueprint(app)
        logger.info("Performance optimization API blueprint registered: /api/performance/*")
    except Exception as e:
        logger.warning(f"性能监控蓝图注册失败（不影响核心功能）: {e}")
