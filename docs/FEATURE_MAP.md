# 功能边界图(Feature Map)

> 单一事实来源:每个业务功能**只在一个地方**有实现;其它位置要么是路由挂载,要么是过渡 shim。
>
> 本文件与源码同步维护,破坏本约束的 PR 必须被拒绝。

## 三条硬规则

1. **服务端代码只许新写到 `app/`**。`backend/` 目录已于 **2026-04-20** 全量下线(迁移登记见 [MIGRATION_REGISTRY.md §5](MIGRATION_REGISTRY.md));备份见 [.archive/legacy-backend-2026-04-final/](../.archive/legacy-backend-2026-04-final/)。
2. **前端代码只许写到 `frontend/`**。`static/`、`templates/vue-dist/` 是构建产物,不是源。
3. **服务启动只用 `XCAGI/run.py`**(端口 5000);禁止新增任何其它 HTTP 入口。

## 顶层目录角色

| 目录 | 类型 | 职责 |
|------|------|------|
| [XCAGI/](../XCAGI/) | 启动外壳 | `run.py` 入口、alembic、mods、部署配置、资源。**不含业务代码**(通过 sys.path 加载根 `app/`)。 |
| [app/](../app/) | 服务端唯一代码 | Neuro-DDD 分层:`domain/` / `application/` / `infrastructure/` / `neuro_bus/` / `fastapi_app.py` / `fastapi_routes/`(含历史兼容子集) / `legacy/`(过渡期集中托管的支持模块) / `shell/`。 |
| [frontend/](../frontend/) | 前端唯一代码 | Vue 3 + Vite,`package.json` name = `xcagi-frontend`。 |
| [mods/](../mods/) | 模块包 | 行业包(奇士美、太阳鸟等),运行时被 `XCAGI/mods/` 加载。 |
| [MODstore/](../MODstore/) | 独立产品子线 | MOD 市场,单独部署,不是主应用的一部分。 |
| [WXCC/](../WXCC/) | 独立产品子线 | 微信小程序,不是主应用运行时的一部分(主应用只暴露 `/api/mp*` 给它调)。 |
| [mobile-android/](../mobile-android/) | 独立客户端 | Kotlin + Compose 原生 App;调 FHD `/api/mobile/v1` 与 MODstore 公网 API。见 [guides/MOBILE_ANDROID.md](./guides/MOBILE_ANDROID.md)。 |
| [rasa/](../rasa/) | NLU 训练数据 | 训练 Rasa 模型用,非运行时代码。 |
| [scripts/](../scripts/) | 运维/开发脚本 | `dev/` 开发调试,`launchers/` 辅助启动,`backend-legacy/` 历史脚本。 |
| [tests/](../tests/) | 正式测试 | `pytest.ini testpaths=tests`。 |
| [docs/](../docs/) | 文档 | `reports/` 历史迁移/评估报告,`guides/` 操作指南,`user-guides/` 用户手册。 |
| [resources/](../resources/) | 运行时资源 | 配置、解密工具、tools_legacy、字体等。 |
| [data/](../data/) | 运行时数据 | `dev-db/` 本地 SQLite,生产应用 Postgres。已 gitignored。 |
| [k8s/](../k8s/) | 部署清单 | Kubernetes manifest + monitoring。 |
| [alembic/](../alembic/) | DB 迁移 | alembic 生成的 versions。 |
| [.archive/](../.archive/) | 归档(本地) | 历史二进制、业务样本。已 gitignored。 |
| [.secrets/](../.secrets/) | 敏感文件(本地) | Alipay 公钥、私钥等。已 gitignored。 |

## 功能落点

### AI 聊天 / Chat

- HTTP:[app/routes/ai_chat.py](../app/routes/ai_chat.py) + [app/fastapi_routes/xcagi_compat.py](../app/fastapi_routes/xcagi_compat.py) 的 `/api/ai/chat`(Vue 客户端主用)
- 应用服务:[app/application/ai_chat_app_service.py](../app/application/ai_chat_app_service.py)
- 工作流:[app/application/workflow/](../app/application/workflow/) + [app/legacy/planner.py](../app/legacy/planner.py)(过渡)
- 工具调用:[app/legacy/tools.py](../app/legacy/tools.py)(后续继续拆到 `app/application/workflow/tools.py`)
- LLM 路由:[app/legacy/llm_config.py](../app/legacy/llm_config.py)、[app/legacy/ai_model_registry.py](../app/legacy/ai_model_registry.py)(后续继续拆到 `app/infrastructure/ai/`)
- 意图:[app/ai_engines/deepseek/intent_service.py](../app/ai_engines/deepseek/intent_service.py) + [app/services/deepseek_intent_service.py](../app/services/deepseek_intent_service.py) + [app/services/rasa_nlu_service.py](../app/services/rasa_nlu_service.py)
- 神经域:[app/neuro_bus/domains/ai_service_domain.py](../app/neuro_bus/domains/ai_service_domain.py) + [app/neuro_bus/domains/intent_domain.py](../app/neuro_bus/domains/intent_domain.py)

### 发货单 / Shipment

- 应用服务:[app/application/shipment_app_service_v2.py](../app/application/shipment_app_service_v2.py)
- 聚合根:[app/domain/aggregates/shipment_aggregate.py](../app/domain/aggregates/shipment_aggregate.py)
- 仓储接口:[app/domain/repositories/shipment_repository.py](../app/domain/repositories/shipment_repository.py)
- 持久化:[app/db/models/shipment.py](../app/db/models/shipment.py)
- HTTP(新):[app/fastapi_routes/shipment/](../app/fastapi_routes/shipment/)
- HTTP(compat):[app/fastapi_routes/shipment_orders.py](../app/fastapi_routes/shipment_orders.py) + `/api/shipment/create|list`([app/fastapi_routes/miniprogram.py](../app/fastapi_routes/miniprogram.py))
- 文档生成:[app/infrastructure/documents/shipment_document_generator_impl.py](../app/infrastructure/documents/shipment_document_generator_impl.py)
- 神经域事件:[app/neuro_bus/domains/shipment_domain.py](../app/neuro_bus/domains/shipment_domain.py) + [app/neuro_bus/events/shipment_events.py](../app/neuro_bus/events/shipment_events.py)

### 标签打印 / Label

- 模板生成器:[app/infrastructure/skills/label_template_generator/](../app/infrastructure/skills/label_template_generator/)
- 运行时生成:同 `shipment_document_generator_impl.py`(PIL 画图)
- HTTP:[app/fastapi_routes/print_routes.py](../app/fastapi_routes/print_routes.py) `/api/print/*`
- **单张标签打印**:`POST /api/print/single_label` → 实现在 [app/fastapi_routes/ai_assistant.py](../app/fastapi_routes/ai_assistant.py) `compat_print_single_label` → 调 [app/application/print_app_service.py](../app/application/print_app_service.py) `PrintApplicationService.print_single_label`
- **工作流标签调度**:`POST /api/print/workflow/label-print/dispatch` 幂等接口（含产品查找 + 打印）
- **商标监控**:不是代码功能,只是 BarTender 使用说明。见 [docs/user-guides/bartender/](./user-guides/bartender/)。

### 微信 / WeChat

- 联系人同步:[app/services/wechat_contact_service.py](../app/services/wechat_contact_service.py)、[app/services/wechat_contact_cache_import.py](../app/services/wechat_contact_cache_import.py)
- 消息与任务:[app/services/wechat_task_service.py](../app/services/wechat_task_service.py)
- 持久化:[app/infrastructure/persistence/wechat_contact_store_impl.py](../app/infrastructure/persistence/wechat_contact_store_impl.py)
- 神经域:[app/neuro_bus/domains/wechat_domain.py](../app/neuro_bus/domains/wechat_domain.py)
- 小程序 HTTP:[app/routes/wechat_miniprogram.py](../app/routes/wechat_miniprogram.py) + [app/fastapi_routes/miniprogram.py](../app/fastapi_routes/miniprogram.py)
- **解密工具**(外部进程):[resources/wechat-decrypt/](../resources/wechat-decrypt/)、[XCAGI/WechatDecrypt/](../XCAGI/WechatDecrypt/)(二进制构建)
- 客户端:[WXCC/](../WXCC/)(独立小程序源码)

### 支付 / Payment(支付宝)

- **实现**:[app/infrastructure/payment/alipay.py](../app/infrastructure/payment/alipay.py) + [app/infrastructure/payment/order_store.py](../app/infrastructure/payment/order_store.py)
- HTTP:[app/fastapi_routes/model_payment.py](../app/fastapi_routes/model_payment.py) `/api/model-payment/*`(通知路径 `/api/model-payment/notify/alipay`)
- 神经域:[app/neuro_bus/domains/payment_domain.py](../app/neuro_bus/domains/payment_domain.py)
- 配置:根 `.env`(公钥/私钥路径),公钥仅放 `.secrets/alipay/`
- 独立目录:[alipay_package/](../alipay_package/) 含同名 `model_payment_compat.py` 副本(待去重,见 3.2)

### OCR / NLU

- OCR 服务:[app/services/ocr_service.py](../app/services/ocr_service.py) + [app/application/ocr_app_service.py](../app/application/ocr_app_service.py)
- 神经域:[app/neuro_bus/domains/ocr_domain.py](../app/neuro_bus/domains/ocr_domain.py)
- Rasa 包装:[app/services/rasa_nlu_service.py](../app/services/rasa_nlu_service.py) + [app/services/train_intent.py](../app/services/train_intent.py)
- Rasa 数据:[rasa/](../rasa/)

### Mods / 模块市场

> **解耦策略（2026）**：新业务只做 Mod（房子）或 `employee_pack`（家具）；宿主能力清单见 [guides/PLATFORM_SHELL.md](./guides/PLATFORM_SHELL.md) 与 `GET /api/platform-shell/capabilities`。客户 Mod `taiyangniao-pro`、`sz-qsm-pro` 禁止删除。

- 运行时加载:[app/infrastructure/mods/](../app/infrastructure/mods/)
- 发现外壳:[app/shell/xcagi_mods_discover.py](../app/shell/xcagi_mods_discover.py)
- 模块源:[mods/](../mods/) + [XCAGI/mods/](../XCAGI/mods/)(运行时挂载)
- 市场 UI(独立子线):[MODstore/](../MODstore/)

### 模板 / 单据

- 模板服务:[app/fastapi_routes/template_api.py](../app/fastapi_routes/template_api.py) + [app/legacy/document_template_service.py](../app/legacy/document_template_service.py)(后续继续拆到 `app/application/templates/`)
- HTTP:[app/fastapi_routes/document_templates.py](../app/fastapi_routes/document_templates.py) `/api/document-templates/*`、[app/fastapi_routes/excel_templates.py](../app/fastapi_routes/excel_templates.py) `/api/excel/*`
- Excel 导入/生成:[app/legacy/customers_excel_import.py](../app/legacy/customers_excel_import.py)、[app/legacy/products_bulk_import.py](../app/legacy/products_bulk_import.py)、[app/legacy/sales_contract_excel_generate.py](../app/legacy/sales_contract_excel_generate.py)、[app/legacy/price_list_docx_export.py](../app/legacy/price_list_docx_export.py)(全部计划继续拆到 `app/application/` 或 `app/infrastructure/documents/`)
- **价格表导出工具**:`handle_price_list_export` 已迁至 [app/application/tools/exports.py](../app/application/tools/exports.py) — 从 `app.application.tools` 导入

## 非代码功能澄清

- **"商标监控"**:原仓根 `监控/商标监控使用说明.txt`——BarTender 用户手册,**没有代码**。已整合到 [docs/user-guides/bartender/](./user-guides/bartender/)。
- **"软著申请"**:软件著作权申请资料,**没有代码**。位于仓根 `软著申请/`,建议归档到 `docs/legal/`(本次未动,以免丢失原始路径)。

## 待归并项(未来 PR)

- `alipay_package/model_payment_compat.py` 是 `app/fastapi_routes/model_payment.py` 的旧副本,应删除。
- `static/` vs `frontend/public/static/`:保留一份,主应用用 `frontend/dist` 或 `templates/vue-dist`。
- `resources/tools_legacy/AI助手/` vs `XCAGI/resources/tools_legacy/AI助手/`:保留 `XCAGI/` 下的(运行时加载),归档另一份。
- `WechatDecrypt/` 位于仓根(看起来是构建产物),`wechat-decrypt/` 也在仓根,两者与 `resources/wechat-decrypt/`、`XCAGI/WechatDecrypt/` 关系需要梳理。
