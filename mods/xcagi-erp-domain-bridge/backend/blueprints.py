"""ERP 领域门面 Mod — 产品 / 客户 / 出货 / 微信；G：产品/出货经 domain_handlers。"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, Query, Request

logger = logging.getLogger(__name__)

HOST_DOMAIN_PREFIXES = [
    "/api/products",
    "/api/customers",
    "/api/orders",
    "/api/shipment",
    "/api/wechat",
]


def _invoke(domain: str, action: str, **kwargs: Any):
    from app.mod_sdk.erp_domain_dispatch import invoke_erp_domain_handler

    return invoke_erp_domain_handler(domain, action, **kwargs)


def register_fastapi_routes(app, mod_id: str) -> None:
    router = APIRouter(prefix=f"/api/mod/{mod_id}", tags=[f"erp-domain-{mod_id}"])

    @router.get("/status")
    def status():
        from app.mod_sdk.erp_domain_compat import list_erp_domains_registry
        from app.mod_sdk.erp_domain_dispatch import list_erp_domain_handlers_summary
        from app.mod_sdk.erp_repository_registry import list_erp_repository_registry

        return {
            "success": True,
            "data": {
                **list_erp_domains_registry(),
                "mod_id": mod_id,
                "phase": "L",
                "domain_handlers": list_erp_domain_handlers_summary(),
                "repositories": list_erp_repository_registry(),
            },
        }

    @router.get("/repositories/registry")
    def repositories_registry():
        from app.mod_sdk.erp_repository_registry import list_erp_repository_registry

        return {"success": True, "data": list_erp_repository_registry()}

    @router.get("/domains/registry")
    def domains_registry():
        from app.mod_sdk.erp_domain_compat import list_erp_domains_registry

        return {"success": True, "data": list_erp_domains_registry()}

    # ── 产品（G：domain_handlers → 宿主 Service/DB）────────────────
    @router.get("/products/list")
    def mod_products_list(
        request: Request,
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=20, ge=1, le=2000),
        keyword: str | None = Query(None),
        unit: str | None = Query(None),
    ):
        return _invoke(
            "products",
            "list",
            request=request,
            page=page,
            per_page=per_page,
            keyword=keyword,
            unit=unit,
        )

    @router.get("/products/{product_id:int}")
    def mod_products_get(request: Request, product_id: int):
        return _invoke("products", "get", request=request, product_id=product_id)

    @router.post("/products/add")
    def mod_products_add(request: Request, body: dict | None = Body(default=None)):
        return _invoke("products", "add", request=request, body=body or {})

    @router.post("/products/update")
    def mod_products_update(request: Request, body: dict | None = Body(default=None)):
        return _invoke("products", "update", request=request, body=body or {})

    @router.post("/products/delete")
    def mod_products_delete(request: Request, body: dict | None = Body(default=None)):
        return _invoke("products", "delete", request=request, body=body or {})

    @router.post("/products/batch-delete")
    def mod_products_batch_delete(request: Request, body: dict | None = Body(default=None)):
        return _invoke("products", "batch_delete", request=request, body=body or {})

    @router.get("/products/product_names")
    def mod_products_names():
        return _invoke("products", "product_names")

    @router.get("/products/product_names/search")
    def mod_products_names_search(keyword: str = Query(default="")):
        return _invoke("products", "product_names_search", keyword=keyword)

    @router.post("/products/batch")
    def mod_products_batch(body: dict | None = Body(default=None)):
        return _invoke("products", "batch", body=body or {})

    # ── 客户（G2：domain_handlers）──────────────────────────────────
    @router.get("/customers/list")
    def mod_customers_list(
        request: Request,
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=20, ge=1, le=2000),
        keyword: str | None = Query(None),
    ):
        return _invoke(
            "customers",
            "list",
            request=request,
            page=page,
            per_page=per_page,
            keyword=keyword,
        )

    @router.get("/customers/{customer_id:int}")
    def mod_customers_get(request: Request, customer_id: int):
        return _invoke("customers", "get", request=request, customer_id=customer_id)

    @router.post("/customers")
    def mod_customers_create(request: Request, body: dict | None = Body(default=None)):
        return _invoke("customers", "create", request=request, body=body or {})

    @router.put("/customers/{customer_id:int}")
    def mod_customers_update(
        request: Request, customer_id: int, body: dict | None = Body(default=None)
    ):
        return _invoke(
            "customers",
            "update",
            request=request,
            customer_id=customer_id,
            body=body or {},
        )

    @router.delete("/customers/{customer_id:int}")
    def mod_customers_delete(request: Request, customer_id: int):
        return _invoke("customers", "delete", request=request, customer_id=customer_id)

    # ── 出货（G：ShipmentAppService 经 domain_handlers）──────────────
    @router.get("/shipment/shipment-records/records")
    def mod_shipment_records(
        unit: str | None = Query(default=None),
        unit_name: str | None = Query(default=None),
    ):
        return _invoke("shipment", "records_list", unit=unit, unit_name=unit_name)

    @router.get("/shipment/shipment-records/units")
    def mod_shipment_units():
        return _invoke("shipment", "records_units")

    @router.get("/shipment/download/{filename:path}")
    def mod_shipment_download(filename: str):
        from app.fastapi_routes.shipment_orders import shipment_download

        return shipment_download(filename)

    @router.get("/orders")
    def mod_orders_list(limit: int = Query(default=100, ge=1, le=5000)):
        return _invoke("shipment", "orders_list", limit=limit)

    @router.get("/orders/next_number")
    def mod_orders_next_number(suffix: str = Query(default="A")):
        from app.fastapi_routes.shipment_orders import orders_next_number_under_api

        return orders_next_number_under_api(suffix=suffix)

    @router.get("/purchase_units")
    @router.get("/purchase_units/")
    def mod_purchase_units_list():
        from app.fastapi_routes.xcagi_compat_product import purchase_units_list

        return purchase_units_list()

    @router.get("/purchase_units/by_name/{unit_name:path}")
    def mod_purchase_units_by_name(unit_name: str):
        from app.fastapi_routes.ai_assistant import compat_purchase_units_by_name

        return compat_purchase_units_by_name(unit_name)

    # ── 微信（G2：WechatContactAppService / TaskAppService）──────────
    @router.get("/wechat/contacts")
    def mod_wechat_contacts(
        keyword: str | None = Query(default=None),
        type: str = Query(default="all"),
        starred: str = Query(default="false"),
        limit: int = Query(default=100),
    ):
        return _invoke(
            "wechat",
            "contacts_list",
            keyword=keyword,
            type=type,
            starred=starred,
            limit=limit,
        )

    @router.get("/wechat/contacts/{contact_id:int}")
    def mod_wechat_contact_get(contact_id: int):
        return _invoke("wechat", "contact_get", contact_id=contact_id)

    @router.get("/wechat/tasks")
    def mod_wechat_tasks(
        status: str = Query(default="pending"),
        contact_id: int | None = Query(default=None),
        limit: int = Query(default=20),
    ):
        return _invoke(
            "wechat",
            "tasks",
            status=status,
            contact_id=contact_id,
            limit=limit,
        )

    import wechat_contacts_routes

    wechat_contacts_routes.mount_wechat_contacts_routes(router)

    app.include_router(router)
    logger.info("xcagi-erp-domain-bridge registered: %s", mod_id)


def mod_init():
    logger.info("xcagi-erp-domain-bridge mod_init (erp domain facade H)")
