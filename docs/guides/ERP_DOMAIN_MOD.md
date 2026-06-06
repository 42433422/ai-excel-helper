# 里程碑 C / G：ERP 领域门面 Mod

## Mod（房子）

- id：`xcagi-erp-domain-bridge`
- 安装：`mods/xcagi-erp-domain-bridge/`
- v1.4.0：里程碑 H — 客户 `CustomerApplicationService` + `wechat_contacts` 门面代理

## 覆盖领域

| 领域 | 门面前缀 | G2 handler | 数据层 |
|------|----------|------------|--------|
| 产品 | `/products/*` | ✅ Mod + `ProductsService` | 宿主 Repository（G+ 不再走 compat raw SQL） |
| 出货 | `/shipment/*`、`/orders` | ✅ Mod | 宿主 `ShipmentAppService` |
| 客户 | `/customers/*` | ✅ Mod + `CustomerApplicationService` | 宿主 Repository |
| 微信 | `/wechat/*` | ✅ Mod | 宿主 `WechatContactAppService` / `WechatTaskAppService` |

## API

- `GET /api/mod/xcagi-erp-domain-bridge/status`（含 `domain_handlers` 摘要）
- `GET /api/mod/xcagi-erp-domain-bridge/domains/registry`
- 各领域 CRUD 与宿主路径对齐，前缀为 Mod

## 分派链（G）

```
前端 → Mod 路由 → erp_domain_dispatch → domain_handlers.py → 宿主 Service/DB
宿主 /api/products/list → try_invoke_erp_domain_handler（同 Mod handler，避免双份业务逻辑）
```

返回 JSON 可含 `source: mod:xcagi-erp-domain-bridge`、`execution_path: mod_domain_handler`。

## 前端路径

安装 Mod 后 `mods` store 会设置 `localStorage.xcagi_erp_domain_mod_facade_enabled=1`。

- `products.ts` / `customers.ts`：`resolveErpApiBase()`
- `orders.ts` / `wechat.ts`：`resolveErpApiPath('/api/...')`

## 环境变量

| 变量 | 作用 |
|------|------|
| `XCAGI_ERP_DOMAIN_VIA_MOD=1` | 强制走 Mod 门面 |
| `XCAGI_DISABLE_ERP_DOMAIN_MOD=1` | 禁用门面 |
| `XCAGI_ERP_DOMAIN_HANDLERS=1` | 强制 Mod domain_handlers（含宿主 `/api` 路径） |
| `XCAGI_DISABLE_ERP_DOMAIN_HANDLERS=1` | 禁用 G handler，回退宿主路由 |
| `XCAGI_ERP_PRODUCTS_VIA_SERVICE=1` | 强制产品 CRUD 经 `ProductsService` |
| `XCAGI_DISABLE_ERP_PRODUCTS_VIA_SERVICE=1` | 禁用 G+，产品列表回退 PG 查询层 |

## Repository（里程碑 L++）

- `repository_factory.create_repository_bundle()`：产品/出货仓储 + 客户 `ModCustomersSessionAdapter`
- 宿主 `get_products_service()`、`get_customers_session()` 经 `erp_repository_registry` 解析到 Mod 适配器
- 存储实现仍可委托宿主 SQLAlchemy；**装配边界**在 Mod，替换 `inner` / bundle 即可换实现

## 未迁出

- PostgreSQL 引擎与 ORM 模型仍在宿主
- 安装门面 Mod 后，`/api/wechat_contacts/*` 映射为 `/api/mod/.../wechat_contacts/*`（实现仍委托 compat）

## 同步

```powershell
.\成都修茈科技有限公司\scripts\sync_all_platform_mods_to_fhd.ps1
```
