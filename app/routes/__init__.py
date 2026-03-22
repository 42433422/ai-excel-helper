"""
路由蓝图注册模块

注册所有路由蓝图到 Flask 应用。
"""

from flask import Flask


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
    from .auth import auth_bp, users_bp
    from .conversations import conversations_bp
    from .customers import customers_bp
    from .distillation import distillation_bp
    from .excel_extract import excel_extract_bp
    from .excel_templates import excel_templates_bp
    from .frontend import frontend_bp
    from .health import health_bp
    from .intent import intent_bp
    from .intent_packages import intent_packages_bp
    from .materials import materials_bp
    from .metrics import metrics_bp
    from .ocr import ocr_bp
    from .print import print_bp
    from .products import products_bp
    from .shipment import shipment_bp
    from .skills import skills_bp
    from .system import system_bp
    from .templates import templates_bp
    from .tools import tools_bp
    from .upload import upload_bp
    from .wechat import wechat_bp
    from .wechat_contacts import wechat_contacts_bp

    # 默认分组：两个进程分别承担"材料/基础数据"和"出货/AI 助手/兼容层"。
    groups_map: dict[str, set[str]] = {
        "warehouse": {
            "tools",
            "customers",
            "products",
            "ocr",
            "excel_templates",
            "excel_extract",
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
        },
        "shipment": {
            "frontend",
            "shipment",
            "wechat",
            "wechat_contacts",
            "ai_chat",
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
            "shipment",
            "wechat",
            "wechat_contacts",
            "ai_chat",
            "print",
            "ocr",
            "excel_templates",
            "excel_extract",
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
        app.register_blueprint(frontend_bp)
    if "tools" in chosen:
        app.register_blueprint(tools_bp)
    if "customers" in chosen:
        app.register_blueprint(customers_bp, url_prefix="/api/customers")
    if "products" in chosen:
        app.register_blueprint(products_bp, url_prefix="/api/products")
    if "shipment" in chosen:
        app.register_blueprint(shipment_bp, url_prefix="/api/shipment")
    if "wechat" in chosen:
        # `wechat_bp` 已在自身 Blueprint 定义了 url_prefix=/api/wechat
        # 此处不要再次传 url_prefix，避免前缀重复导致接口 404
        app.register_blueprint(wechat_bp)
    if "wechat_contacts" in chosen:
        app.register_blueprint(wechat_contacts_bp)  # 兼容旧版前端路径
    if "ai_chat" in chosen:
        # `ai_chat_bp` 已在自身 Blueprint 定义了 url_prefix=/api/ai
        app.register_blueprint(ai_chat_bp)
        # AI 产品解析路由与对话路由共用 /api/ai 前缀
        app.register_blueprint(ai_parse_bp)
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
    if "system" in chosen or True:
        app.register_blueprint(system_bp)
