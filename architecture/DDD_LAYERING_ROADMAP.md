# XCAGI 分层与 DDD 归位规划

本文回应三类现状：**路由与服务/领域耦合**、`utils/` **与 DDD 分层错位**、**持久化模型偏贫血**（如 `ShipmentRecord` 仅定义列）。目标是给出**可渐进执行**的边界与迁移顺序，而非一次性大重写。

---

## 1. 目标分层（参考 DDD + 六边形）

| 层 | 职责 | 允许依赖 | 典型位置（已有） |
|----|------|----------|------------------|
| **接口（Interface）** | HTTP/WebSocket、参数校验、状态码、序列化 | Application 或 Facade | `app/routes/*` |
| **应用（Application）** | 用例编排、事务边界、DTO 进出 | Domain、Ports | `app/application/*` |
| **领域（Domain）** | 业务规则、聚合不变量、领域事件（可选） | 标准库、极少共享内核 | `app/domain/*` |
| **端口（Ports）** | 抽象：仓储、网关、文件、消息 | 无实现细节 | `app/application/ports/*` |
| **基础设施（Infrastructure）** | ORM、SQL、第三方 API、文件系统 | Domain、Ports 的实现 | `app/infrastructure/*`、`app/db/*` |

**原则**：路由层**不出现**复杂业务分支、**不直接**访问 ORM `Session`、**不直接**拼 SQL；长流程应落在 `*ApplicationService` 或专用 **Facade**。

---

## 2. 路由与服务耦合：问题形态与改进

### 2.1 典型问题

- **巨型蓝图**：单文件集中大量端点、校验、进度状态、文件读写与领域规则（例如 `routes/templates.py`、`routes/shipment.py` 体量过大），阅读与测试成本高。
- **应用服务入口不统一**：部分路由经 `bootstrap.get_*_app_service()`，部分仍直接 `from app.services import ...` 或 `from app.utils import ...`，边界不一致。
- **进程内全局状态**：如模板分析 `analysis_progress` 字典与锁放在路由模块，扩展多进程/多实例时行为未定义。

### 2.2 规划动作（按优先级）

1. **按用例拆蓝图（P0）**  
   - 例如 `templates`：`analyze`、`crud`、`grid_tool`、`preview` 拆为子模块或子 Blueprint，由 `templates/__init__.py` 注册同一 `url_prefix`。  
   - `shipment`：按「文档生成 / 打印 / 记录 CRUD / 订单号」拆文件，公共 `get_service` 保留一处。

2. **路由瘦身模板（P0）**  
   - 每 handler：`parse_request()` → 调用 **单一** 应用方法 → `format_response()`。  
   - HTTP 层只做：鉴权（若有）、必填校验、错误映射（业务异常 → HTTP 状态码）。

3. **全局状态下沉（P1）**  
   - `analysis_progress` 类状态迁入 **基础设施**（如 Redis/内存 `ProgressStore` 接口 + 默认内存实现），路由只依赖端口接口，便于以后换实现。

4. **OpenAPI/Swagger 与实现同源（P2）**  
   - 大段 `@swag_from` 与实现分叉风险高；长期可迁到 schema 模块或 codegen，与 Pydantic/dataclass 请求体对齐（若技术栈允许）。

---

## 3. `utils/` 与 DDD 归位

### 3.1 分类标准

| 类型 | 归位建议 | 示例（`app/utils`） |
|------|----------|---------------------|
| **纯技术横切** | 保留 `utils/` 或 `infrastructure/shared/` | `logger`、`retry`、`circuit_breaker`、`rate_limiter`、`json_safe` |
| **持久化/外部系统** | `infrastructure/persistence` 或 `infrastructure/external` | `database_service`、`external_sqlite` |
| **业务相关 Excel/模板** | `domain`（规则）+ `infrastructure`（读写）或 `application`（编排） | `excel_template_analyzer`、`template_export_utils`（与模板领域强相关） |
| **与打印/设备相关** | `infrastructure/devices` 或 `infrastructure/printing` | `print_utils`、`printer_automation` |
| **会话/任务上下文** | `infrastructure` 或 `application` 上下文模块 | `task_context`、`user_memory`（若含业务策略则应用层编排） |

### 3.2 迁移顺序建议

1. **先画依赖图**：谁 import 了谁；被路由直接引用的 `utils` 优先迁走或改为经 Application。  
2. **每次只迁一个垂直切片**（例如「模板导出」）：新建 `infrastructure/documents` 或扩展现有 `template_export`，路由改调应用服务。  
3. **避免「大 utils 爆炸」**：新代码禁止在 `utils` 堆业务；新增能力默认落在 `domain` / `application` / `infrastructure` 之一。

---

## 4. 「模型类太简单」（如 `db/models/shipment.py`）

### 4.1 澄清角色

- **`ShipmentRecord`（SQLAlchemy）**：**持久化模型（Persistence Model）**，与表结构一一对应，**短文件是常态**，不等于领域模型简陋。  
- 若业务规则已在 `domain/services/shipment_rules_engine.py`、`domain/shipment/*` 等处表达，则当前拆分是合理的。

### 4.2 何时需要「变厚」

- 若出现：**多处路由/services 重复校验同一组字段**、状态流转散落、金额/数量计算不一致 → 应引入或强化 **领域对象**（如 `ShipmentLine`、`ShipmentAggregate`），ORM 仍保持薄；通过 **Mapper** 或显式工厂在应用层做 DTO ↔ 持久化转换。

### 4.3 规划动作

1. **文档化映射**：在 `domain/shipment/README.md`（或本仓库 architecture 下子页）写明：`ShipmentRecord` 字段与领域概念对应关系。  
2. **富领域优先放在 `domain/`**：不变量、计算、状态机；ORM 不承载业务。  
3. **仅在需要跨聚合复用时**再抽「共享内核」模块，避免过早抽象。

---

## 5. 建议的迭代节奏（与业务并行）

| 阶段 | 内容 | 产出 |
|------|------|------|
| **S1** | 选 1 个最大路由文件拆模块 + 抽 `ProgressStore` 接口（内存实现） | 可读的 PR、无行为变化 |
| **S2** | 梳理 `utils` 清单，迁移 1～2 个强业务模块到 `infrastructure`/`application` | 依赖方向更清晰 |
| **S3** | 发货/模板域补充领域服务单测 + 映射说明 | 降低「25 行模型」带来的误解风险 |

---

## 6. 相关现有资产

- 应用服务与端口：`app/application/`、`app/application/ports/`  
- 领域：`app/domain/`（含 `shipment_rules_engine`、模板解析等）  
- 基础设施实现：`app/infrastructure/`  
- 部分路由已较好：`routes/shipment.py` 头部已使用 `ShipmentApplicationService`（可继续把后半段同样模式化并拆文件）

---

*本文件路径：`architecture/DDD_LAYERING_ROADMAP.md`（不受根目录 `docs/` gitignore 影响，可纳入版本库）。*
