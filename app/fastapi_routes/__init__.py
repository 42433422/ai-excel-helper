"""
FastAPI 路由注册模块

集中注册所有 FastAPI 路由
"""

import importlib
import logging

from fastapi import FastAPI

logger = logging.getLogger(__name__)

# Legacy "gap" domain routers, mounted directly from ``domains/<domain>/routes``
# under full edition (or forced via ``XCAGI_REGISTER_LEGACY_ROUTES=1``).
# Inlined here after physically removing ``legacy_host_routers.py`` (v10 shim 收口).
_LEGACY_GAP_DOMAIN_MODULES: tuple[str, ...] = (
    "app.fastapi_routes.domains.conversation.routes",
    "app.fastapi_routes.domains.excel.routes",
    "app.fastapi_routes.domains.product.routes",
    "app.fastapi_routes.domains.static.routes",
    "app.fastapi_routes.domains.system.routes",
    "app.fastapi_routes.domains.wechat.routes",
    "app.fastapi_routes.domains.shipment.routes",
)


def register_legacy_gap_routers(app: FastAPI) -> None:
    """Mount legacy gap routers directly from ``domains/<domain>/routes``.

    Semantics preserved from the removed
    ``legacy_host_routers.register_legacy_gap_routers``: these routers use
    absolute ``/api/...`` paths, so they are included WITHOUT an extra prefix.
    Empty routers (e.g. inventory stub) are skipped.
    """
    for mod_path in _LEGACY_GAP_DOMAIN_MODULES:
        mod = importlib.import_module(mod_path)
        router = mod.router
        if not router.routes:
            logger.debug("Skipped empty legacy gap router: %s", mod_path)
            continue
        app.include_router(router)
        logger.info(
            "Registered %s (%d routes, deprecated=%s)",
            mod_path,
            len(router.routes),
            getattr(router, "deprecated", False),
        )


def register_all_routes(app: FastAPI) -> None:
    """
    注册所有 FastAPI 路由

    Args:
        app: FastAPI 应用实例
    """
    logger.info("Registering FastAPI routes...")

    # 注册基础设施路由
    _register_infrastructure_routes(app)

    # 注册业务路由
    _register_business_routes(app)

    # 注册健康检查
    _register_health_routes(app)

    # NeuroBus 诊断路由（/api/neurobus/health、/api/neurobus/stats）
    _register_neuro_routes(app)

    _register_neuro_migration_routes(app)

    _register_lan_routes(app)

    # 历史兼容路由(原 ``app.fastapi_compat_routes``,2026-04-20 起内联到此处),
    # 这批路由曾长期挂载在 ``backend/routers/*``,阶段 2–4 已迁至 ``app/fastapi_routes/``。
    _register_legacy_compat_routes(app)

    logger.info("FastAPI routes registered successfully")


def _register_infrastructure_routes(app: FastAPI) -> None:
    """注册基础设施路由"""
    # Mod schema router 是工具模块，没有 FastAPI router 对象
    # 这里可以添加相关健康检查端点
    try:
        from app.fastapi_routes.desktop_runtime import router as desktop_runtime_router

        app.include_router(desktop_runtime_router)
        logger.info("Registered desktop_runtime_router (/api/desktop/*)")
    except Exception as e:
        logger.warning("Desktop runtime routes skipped: %s", e)
    try:
        from app.fastapi_routes.desktop_automation import router as desktop_automation_router

        app.include_router(desktop_automation_router)
        logger.info("Registered desktop_automation_router (/api/desktop/automation/*)")
    except Exception as e:
        logger.warning("Desktop automation routes skipped: %s", e)

    # P1-3（2026-06-02）：GDPR 数据主体 API（Article 15/16/17/20）
    try:
        from app.fastapi_routes.gdpr import router as gdpr_router

        app.include_router(gdpr_router)
        logger.info("Registered gdpr_router (/api/gdpr/*)")
    except Exception as e:
        logger.warning("GDPR routes skipped: %s", e)
    logger.debug("Infrastructure routes registered (mod_schema_router is utility module)")


def _register_business_routes(app: FastAPI) -> None:
    """注册业务路由"""
    # ── XCmax 服务器后台控制面 ─────────────────────────────────────
    try:
        from app.fastapi_routes.xcmax_admin import router as xcmax_admin_router

        app.include_router(xcmax_admin_router)
        logger.info("Registered xcmax_admin_router (/api/xcmax/*)")
    except Exception as e:
        logger.warning("xcmax_admin router not available: %s", e)

    # ── 新增一类业务领域路由 ──────────────────────────────────────
    try:
        from app.fastapi_routes.purchase import router as purchase_router

        app.include_router(purchase_router)
        logger.info("Registered purchase router (/api/purchase/*)")
    except (ImportError, AttributeError) as e:
        logger.warning("purchase router not available: %s", e)

    try:
        from app.fastapi_routes.inventory import router as inventory_router

        app.include_router(inventory_router)
        logger.info("Registered inventory router (/api/inventory/*)")
    except (ImportError, AttributeError) as e:
        logger.warning("inventory router not available: %s", e)

    try:
        from app.fastapi_routes.finance_unified_ledger import (
            router as finance_unified_ledger_router,
        )

        app.include_router(finance_unified_ledger_router)
        logger.info("Registered finance unified-ledger router (/api/finance/unified-ledger)")
    except (ImportError, AttributeError) as e:
        logger.warning("finance unified-ledger router not available: %s", e)

    try:
        from app.fastapi_routes.finance_invoices_api import router as finance_invoices_router

        app.include_router(finance_invoices_router)
        logger.info("Registered finance invoices router (/api/finance/invoices/*)")
    except (ImportError, AttributeError) as e:
        logger.warning("finance invoices router not available: %s", e)

    try:
        from app.fastapi_routes.finance import router as finance_router

        app.include_router(finance_router)
        logger.info("Registered finance router (/api/finance/*)")
    except (ImportError, AttributeError) as e:
        logger.warning("finance router not available: %s", e)

    try:
        from app.fastapi_routes.reports import router as reports_router

        app.include_router(reports_router)
        logger.info("Registered reports router (/api/report/*)")
    except (ImportError, AttributeError) as e:
        logger.warning("reports router not available: %s", e)

    try:
        from app.fastapi_routes.rbac import router as rbac_router

        app.include_router(rbac_router)
        logger.info("Registered rbac router (/api/rbac/*)")
    except (ImportError, AttributeError) as e:
        logger.warning("rbac router not available: %s", e)

    # ── 原有基础设施路由 ──────────────────────────────────────────
    # ``/api/system/*`` 改在 ``_register_legacy_compat_routes`` 内、早于 ``xcagi_compat`` 注册，
    # 避免与兼容层 ``/api/system/industry`` 占位路由在匹配顺序上冲突导致 404。

    try:
        from app.fastapi_routes.mods_routes import get_mods_router

        mods_router = get_mods_router()
        app.include_router(mods_router)
        logger.info("Registered mods_router (/api/mods/*)")
    except (ImportError, AttributeError) as e:
        logger.warning(f"Mods router not available: {e}")

    try:
        from app.fastapi_routes.platform_shell_routes import router as platform_shell_router

        app.include_router(platform_shell_router)
        logger.info("Registered platform_shell_router (/api/platform-shell/*)")
    except (ImportError, AttributeError) as e:
        logger.warning("platform_shell router not available: %s", e)

    try:
        from app.fastapi_routes.business_api import router as business_bridge_router

        app.include_router(business_bridge_router)
        logger.info("Registered business_bridge_router (/api/business/*)")
    except (ImportError, AttributeError) as e:
        logger.warning("business_bridge router not available: %s", e)

    # MOD 扩展 / 系统设置「网页同步」等：主栈 run.py:5000 注册 /api/mod-store。
    try:
        from app.fastapi_routes.mod_store_routes import router as mod_store_router

        app.include_router(mod_store_router, prefix="/api/mod-store")
        logger.info("Registered mod_store_router (/api/mod-store/*)")
    except Exception as e:
        logger.warning("mod_store router not available: %s", e)

    try:
        from app.control.routes import router as control_router

        app.include_router(control_router, prefix="/api/control", tags=["control"])
        logger.info("Registered control_router")
    except (ImportError, AttributeError) as e:
        logger.debug(f"Control router not available: {e}")

    try:
        from app.fastapi_routes.voice_routes import router as voice_router

        app.include_router(voice_router)
        logger.info("Registered voice_router (/api/voice/*)")
    except (ImportError, AttributeError) as e:
        logger.warning(f"Voice router not available: {e}")

    try:
        from app.fastapi_routes.mobile_api import router as mobile_api_router

        app.include_router(mobile_api_router)
        logger.info("Registered mobile_api_router (/api/mobile/v1/*)")
    except Exception as e:
        logger.warning("mobile_api router not available: %s", e)


def _register_health_routes(app: FastAPI) -> None:
    """注册健康检查路由"""

    @app.get("/api/health", tags=["health"])
    async def health_check():
        payload: dict = {
            "status": "healthy",
            "version": "1.0.0",
            "service": "xcagi-fastapi",
        }
        try:
            from app.neuro_bus.integrations.fastapi_integration import get_neurobus_health
            from app.neuro_bus.integrations.intent_integration import is_neuro_stack_enabled

            if is_neuro_stack_enabled():
                payload["neuro"] = get_neurobus_health()
            else:
                payload["neuro"] = {"enabled": False}
        except Exception as exc:
            payload["neuro"] = {"enabled": True, "error": str(exc)}
        return payload

    @app.get("/api/ping", tags=["health"])
    async def ping():
        return {"pong": True}

    logger.info("Registered health check routes")


def _register_neuro_routes(app: FastAPI) -> None:
    """注册 NeuroBus HTTP 诊断路由（与 lifespan 中的总线启动配合）。"""
    try:
        from app.neuro_bus.integrations.fastapi_integration import add_neurobus_routes

        add_neurobus_routes(app)
        logger.info("Registered NeuroBus routes (/api/neurobus/*)")
    except Exception as e:
        logger.warning("NeuroBus routes skipped: %s", e)


def _register_neuro_migration_routes(app: FastAPI) -> None:
    try:
        from app.fastapi_routes.neuro_migration_routes import router as neuro_migration_router

        app.include_router(neuro_migration_router)
        logger.info("Registered neuro migration routes (/api/neuro/*)")
    except Exception as e:
        logger.warning("Neuro migration routes skipped: %s", e)


def _register_lan_routes(app: FastAPI) -> None:
    """注册局域网授权用户端 + 管理员路由（/api/lan/*）。"""
    try:
        from app.fastapi_routes.lan_routes import router as lan_router

        app.include_router(lan_router)
        logger.info("Registered LAN routes (/api/lan/*)")
    except Exception as e:
        logger.warning("LAN routes skipped: %s", e)

    try:
        from app.fastapi_routes.lan_admin_routes import router as lan_admin_router

        app.include_router(lan_admin_router)
        logger.info("Registered LAN admin routes (/api/lan/admin/*)")
    except Exception as e:
        logger.warning("LAN admin routes skipped: %s", e)

    try:
        from app.fastapi_routes.lan_settings_routes import router as lan_settings_router

        app.include_router(lan_settings_router)
        logger.info("Registered LAN settings routes (/api/lan/admin/settings)")
    except Exception as e:
        logger.warning("LAN settings routes skipped: %s", e)


def _register_legacy_compat_routes(app: FastAPI) -> None:
    """注册 XCAGI 前端依赖的历史兼容路由(原 backend.routers.*,2026-04-20 已全部迁至本包)。

    ``xcagi_compat`` 路由注册顺序说明:
    主站 Vue 依赖 xcagi_compat(Planner / run_agent_chat)的 JSON 契约与错误语义。
    """

    # 须早于 xcagi_compat：避免与其它 /api 聚合路由在个别 Starlette 版本下的匹配顺序边缘问题，
    # 并保证 /api/market/* 始终由 market_account 提供（compat 层不再重复注册 llm-catalog）。
    from app.fastapi_routes.market_account import router as market_account_router

    app.include_router(market_account_router)
    logger.info("Registered market_account (/api/market/*)")

    from app.fastapi_routes.fhd_meta import router as fhd_meta_router

    app.include_router(fhd_meta_router)
    logger.info("Registered fhd_meta_router (/api/fhd/db-tokens/status)")

    from app.fastapi_routes.debug_client_log import router as debug_client_log_router

    app.include_router(debug_client_log_router)
    logger.info("Registered debug_client_log_router (/api/debug/client-log)")

    # 须早于 xcagi_compat / SPA 兜底：避免 ``GET /api/auth/session/validate`` 等落入 ``/{fallback:path}`` 返回 404。
    from app.fastapi_routes.domains.auth.routes import router as legacy_auth_router

    app.include_router(legacy_auth_router)
    logger.info("Registered legacy_auth_router early (/api/auth/*)")

    try:
        from app.fastapi_routes.system_routes import router as system_router

        app.include_router(system_router)
        logger.info("Registered system_router early (/api/system/*)")
    except (ImportError, AttributeError) as e:
        logger.warning("System router not available: %s", e)

    from app.fastapi_routes.code_editor import router as code_editor_router

    app.include_router(code_editor_router)
    logger.info("Registered code_editor_router (/api/code-editor/*)")

    try:
        from app.fastapi_routes.private_db_read_assistant_compat import (
            register_private_db_read_assistant_routes,
        )

        register_private_db_read_assistant_routes(app)
    except Exception as e:
        logger.warning("private_db_read_assistant compat routes skipped: %s", e)

    try:
        from app.fastapi_routes.user_cs_wechat_passive_compat import (
            register_user_cs_wechat_passive_routes,
        )

        register_user_cs_wechat_passive_routes(app)
    except Exception as e:
        logger.warning("user_cs_wechat_passive compat routes skipped: %s", e)

    try:
        from app.fastapi_routes.wechat_decrypt_routes import router as wechat_decrypt_router

        app.include_router(wechat_decrypt_router)
        logger.info("Registered wechat_decrypt_router (/api/wechat/decrypt/*)")
    except Exception as e:
        logger.warning("wechat_decrypt routes skipped: %s", e)

    from app.fastapi_routes.xcagi_compat import router as xcagi_compat_router

    app.include_router(xcagi_compat_router, prefix="/api")
    logger.info("Registered xcagi_compat_router (prefix=/api)")

    from app.fastapi_routes.document_templates import public_router as doc_templates_public_router

    app.include_router(doc_templates_public_router)
    logger.info("Registered document_templates public_router (/api/document-templates)")

    from app.fastapi_routes.xcagi_startup import router as xcagi_startup_router

    app.include_router(xcagi_startup_router, prefix="/api")
    logger.info("Registered xcagi_startup_router (/api/startup/status)")

    from app.fastapi_routes.template_api import router as template_list_router

    app.include_router(template_list_router)
    logger.info("Registered template_api router (/api/templates*)")

    from app.fastapi_routes.shipment_orders import router as shipment_orders_router

    app.include_router(shipment_orders_router)
    logger.info("Registered shipment_orders (/api/orders*, /api/shipment/shipment-records/*)")

    from app.fastapi_routes.materials import router as materials_router

    app.include_router(materials_router)
    logger.info("Registered materials (/api/materials*)")

    from app.fastapi_routes.upload import router as upload_router

    app.include_router(upload_router)
    logger.info("Registered upload (/api/upload/*)")

    from app.fastapi_routes.ocr import router as ocr_router

    app.include_router(ocr_router)
    logger.info("Registered ocr (/api/ocr/*)")

    from app.fastapi_routes.print_routes import router as print_router

    app.include_router(print_router)
    logger.info("Registered print_routes (/api/print/*)")

    from app.fastapi_routes.ai_assistant import router as ai_assistant_router

    app.include_router(ai_assistant_router)
    logger.info("Registered ai_assistant (/health, /api/generate, /api/shipment-records/*, ...)")

    try:
        from app.fastapi_routes.tts_install import router as tts_install_router

        app.include_router(tts_install_router)
        logger.info("Registered tts_install (/api/tts/install-system-voice)")
    except Exception as e:  # pragma: no cover — Windows-only 可选功能
        logger.warning("tts_install route skipped: %s", e)

    from app.fastapi_routes.excel_templates import router as excel_templates_router

    app.include_router(excel_templates_router)
    logger.info("Registered excel_templates (/api/excel/*)")

    from app.fastapi_routes.excel_extract import router as excel_extract_router

    app.include_router(excel_extract_router)
    logger.info("Registered excel_extract (/api/excel/data/*)")

    from app.fastapi_routes.excel_vector import router as excel_vector_router

    app.include_router(excel_vector_router)
    logger.info("Registered excel_vector (/api/excel/vector/*)")

    from app.fastapi_routes.health_k8s import router as health_k8s_router

    app.include_router(health_k8s_router)
    logger.info("Registered health_k8s (/health/liveness|readiness|details)")

    from app.fastapi_routes.state import router as state_router

    app.include_router(state_router)
    logger.info("Registered state (/api/state/*)")

    from app.fastapi_routes.model_payment import router as model_payment_router

    app.include_router(model_payment_router)
    logger.info("Registered model_payment (/api/model-payment/*)")

    from app.fastapi_routes.payment_reconcile_internal_api import (
        router as payment_reconcile_internal_router,
    )

    app.include_router(payment_reconcile_internal_router)
    logger.info("Registered payment_reconcile_internal (/api/internal/payment/*)")

    from app.fastapi_routes.sales_contract_api import router as sales_contract_router

    app.include_router(sales_contract_router)
    logger.info("Registered sales_contract (/api/sales-contract/*)")

    from app.fastapi_routes.contract_lifecycle_api import router as contract_lifecycle_router

    app.include_router(contract_lifecycle_router)
    logger.info("Registered contract_lifecycle (/api/contract-lifecycle/*)")

    from app.fastapi_routes.operations_line_api import router as operations_line_router

    app.include_router(operations_line_router)
    logger.info("Registered operations_line (/api/operations-line/*)")

    from app.fastapi_routes.ai_intent import router as ai_intent_router

    app.include_router(ai_intent_router)
    logger.info(
        "Registered ai_intent (/api/ai/test, /api/ai/chat-unified*, /api/ai/intent/test, /api/intent/*)"
    )

    from app.fastapi_routes.ai_kitten import router as ai_kitten_router

    app.include_router(ai_kitten_router)
    logger.info("Registered ai_kitten (/api/ai/kitten/*)")

    from app.fastapi_routes.ai_qclaw import router as ai_qclaw_router

    app.include_router(ai_qclaw_router)
    logger.info("Registered ai_qclaw (/api/ai/qclaw/*)")

    from app.mod_sdk.edition_policy import (
        resolve_edition,
        should_register_host_legacy_routes,
    )

    if should_register_host_legacy_routes():
        register_legacy_gap_routers(app)
    else:
        logger.info(
            "Skipped legacy gap routers (edition=%s, set XCAGI_REGISTER_LEGACY_ROUTES=1 to force)",
            resolve_edition(),
        )

    from app.fastapi_routes.approval import router as approval_router

    app.include_router(approval_router)
    logger.info("Registered approval (/api/approval/requests*, /api/approval/flows*)")

    try:
        from app.fastapi_routes.service_bridge import router as service_bridge_router

        app.include_router(service_bridge_router)
        logger.info("Registered service_bridge (/api/service-bridge/*)")
    except Exception as e:
        logger.warning("service_bridge router not available: %s", e)
