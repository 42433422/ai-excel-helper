"""
路由蓝图注册模块

注册所有路由蓝图到 Flask 应用。
"""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    """
    注册所有路由蓝图

    Args:
        app: Flask 应用实例
    """
    from .frontend import frontend_bp
    from .tools import tools_bp
    from .customers import customers_bp
    from .products import products_bp
    from .shipment import shipment_bp
    from .wechat import wechat_bp
    from .wechat_contacts import wechat_contacts_bp
    from .ai_chat import ai_chat_bp
    from .print import print_bp
    from .ocr import ocr_bp
    from .excel_templates import excel_templates_bp
    from .excel_extract import excel_extract_bp
    from .materials import materials_bp
    from .conversations import conversations_bp
    from .distillation import distillation_bp

    app.register_blueprint(frontend_bp)
    app.register_blueprint(tools_bp)
    app.register_blueprint(customers_bp, url_prefix="/api/customers")
    app.register_blueprint(products_bp, url_prefix="/api/products")
    app.register_blueprint(shipment_bp, url_prefix="/api/shipment")
    app.register_blueprint(wechat_bp, url_prefix="/api/wechat")
    app.register_blueprint(wechat_contacts_bp)  # 兼容旧版前端路径
    app.register_blueprint(ai_chat_bp, url_prefix="/api/ai")
    app.register_blueprint(print_bp, url_prefix="/api/print")
    app.register_blueprint(ocr_bp, url_prefix="/api/ocr")
    app.register_blueprint(excel_templates_bp, url_prefix="/api/excel")
    app.register_blueprint(excel_extract_bp, url_prefix="/api/excel/data")
    app.register_blueprint(materials_bp)
    app.register_blueprint(conversations_bp)
    app.register_blueprint(distillation_bp)
