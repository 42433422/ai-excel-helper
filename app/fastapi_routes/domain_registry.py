"""
domain_registry.py — 14+ 业务域 SSOT（v10.0.5+ 纯文档表）

v10.0.3 已删除全部 legacy_/xcagi_compat_* shim；运行时路由由 domains/* 与
``register_legacy_gap_routers``（内联于 ``app/fastapi_routes/__init__.py``）承载。
本模块仅登记业务域 → 目标模块映射，供 CI 与迁移文档使用。
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

BUSINESS_DOMAINS: tuple[str, ...] = (
    "auth",
    "conversation",
    "customer",
    "excel",
    "inventory",
    "misc",
    "product",
    "shipment",
    "static",
    "system",
    "template",
    "wechat",
    "workflow",
    "db",
)

DOMAIN_TO_DIR: dict[str, str] = {
    "auth": "app/fastapi_routes/domains/auth/",
    "conversation": "app/fastapi_routes/domains/conversation/",
    "customer": "app/fastapi_routes/domains/customer/",
    "excel": "app/fastapi_routes/domains/excel/",
    "inventory": "app/fastapi_routes/domains/inventory/",
    "misc": "app/fastapi_routes/domains/misc/",
    "product": "app/fastapi_routes/domains/product/",
    "shipment": "app/fastapi_routes/domains/shipment/",
    "static": "app/fastapi_routes/domains/static/",
    "system": "app/fastapi_routes/domains/system/",
    "template": "app/fastapi_routes/domains/template/",
    "wechat": "app/fastapi_routes/domains/wechat/",
    "workflow": "app/fastapi_routes/domains/workflow/",
    "db": "app/fastapi_routes/domains/db/",
}

ALLOWED_LEGACY_FILES: frozenset[str] = frozenset({"xcagi_compat.py"})


@dataclass(frozen=True)
class LegacyRoute:
    """业务域文档条目（每域一行；不再逐已删 shim filename 登记）"""

    target_domain: str
    target_module: str
    note: str = ""
    filename: str = ""

    def __post_init__(self) -> None:
        if not self.filename:
            object.__setattr__(self, "filename", f"domain:{self.target_domain}")


def _doc(domain: str, module: str, note: str = "") -> LegacyRoute:
    return LegacyRoute(
        target_domain=domain,
        target_module=module,
        note=note,
        filename=f"domain:{domain}",
    )


LEGACY_ROUTE_REGISTRY: tuple[LegacyRoute, ...] = (
    _doc("auth", "app.fastapi_routes.domains.auth.routes", "认证/授权"),
    _doc(
        "conversation",
        "app.fastapi_routes.domains.conversation.routes",
        "对话/聊天（含 AI chat）",
    ),
    _doc("customer", "app.fastapi_routes.domains.customer.routes", "客户/CRM"),
    _doc("excel", "app.fastapi_routes.domains.excel.routes", "Excel 解析/导出"),
    _doc("inventory", "app.fastapi_routes.domains.inventory.routes", "库存"),
    _doc(
        "misc",
        "app.fastapi_routes.domains.misc.helpers",
        "杂项 helpers；compat 聚合见 xcagi_compat.py",
    ),
    _doc("product", "app.fastapi_routes.domains.product.routes", "产品/商品"),
    _doc("shipment", "app.fastapi_routes.domains.shipment.routes", "发货/物流"),
    _doc("static", "app.fastapi_routes.domains.static.routes", "静态资源"),
    _doc("system", "app.fastapi_routes.domains.system.routes", "系统/管理"),
    _doc("template", "app.fastapi_routes.domains.template.routes", "模板"),
    _doc("wechat", "app.fastapi_routes.domains.wechat.routes", "微信域"),
    _doc("workflow", "app.fastapi_routes.domains.workflow.routes", "工作流/审批"),
    _doc("db", "app.fastapi_routes.domains.db.base", "DB 查询/写入（base 入口）"),
)


def get_routes_by_domain(domain: str) -> list[LegacyRoute]:
    return [r for r in LEGACY_ROUTE_REGISTRY if r.target_domain == domain]


def get_pending_domains() -> list[str]:
    project_root = Path(__file__).resolve().parent.parent.parent
    pending = []
    for domain in BUSINESS_DOMAINS:
        target_dir = project_root / DOMAIN_TO_DIR[domain].replace("app/", "app/")
        if not target_dir.exists():
            pending.append(domain)
    return pending


def verify_registry_integrity() -> list[str]:
    errors: list[str] = []

    if not BUSINESS_DOMAINS:
        errors.append("BUSINESS_DOMAINS 为空")

    for d in BUSINESS_DOMAINS:
        if d not in DOMAIN_TO_DIR:
            errors.append(f"业务域 {d} 缺少 DOMAIN_TO_DIR 映射")

    project_root = Path(__file__).resolve().parent.parent.parent
    legacy_dir = project_root / "app" / "fastapi_routes"
    on_disk_legacy: set[str] = set()
    for p in legacy_dir.iterdir():
        if p.name.startswith("__") or p.suffix != ".py":
            continue
        if p.name.startswith("legacy_") or p.name.startswith("xcagi_compat"):
            on_disk_legacy.add(p.name)

    unexpected = on_disk_legacy - ALLOWED_LEGACY_FILES
    if unexpected:
        errors.append(f"未允许的 legacy_/compat_ 顶栏文件: {sorted(unexpected)}")

    registered_domains = {r.target_domain for r in LEGACY_ROUTE_REGISTRY}
    missing_domains = set(BUSINESS_DOMAINS) - registered_domains
    if missing_domains:
        errors.append(f"文档表缺少业务域: {sorted(missing_domains)}")

    for r in LEGACY_ROUTE_REGISTRY:
        if r.target_domain not in BUSINESS_DOMAINS:
            errors.append(f"{r.filename} → 未知业务域: {r.target_domain}")
        if not r.target_module.startswith("app.fastapi_routes.domains."):
            errors.append(f"{r.target_domain} target_module 格式错误: {r.target_module}")

    return errors


if __name__ == "__main__":  # pragma: no cover
    errs = verify_registry_integrity()
    if errs:
        print("❌ 域注册表错误：")
        for e in errs:
            print(f"  - {e}")
        raise SystemExit(1)

    pending = get_pending_domains()
    print(
        f"✅ 域注册表完整 · {len(BUSINESS_DOMAINS)} 业务域 · 文档表 {len(LEGACY_ROUTE_REGISTRY)} 条"
    )
    print(f"📋 待迁移业务域（{len(pending)}/{len(BUSINESS_DOMAINS)}）:")
    for d in pending:
        print(f"  - {d:14}  ({len(get_routes_by_domain(d))} 条文档)")
