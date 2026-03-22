# AI Chat 路由重构计划

## 问题分析

### 当前 `ai_chat.py` (1242 行) 存在的问题：

1. **路由过重** - 单个文件过大，职责过多
2. **直接处理业务逻辑** - 应下沉到 Service 层：
   - `chat()` 中直接调用 `get_products_service()`, `get_customer_app_service()`, `get_shipment_app_service()`
   - `file_analyze()` 直接处理 SQLite 文件读取
   - `import_unit_products()` 直接处理产品导入逻辑
3. **多层嵌套 try-except** - 代码可读性差
4. **混合 Web 响应构建和业务逻辑** - 违反单一职责

---

## 重构目标

1. 将业务逻辑下沉到 Application Service 层
2. 路由层只负责请求解析和响应组装
3. 消除多层嵌套 try-except
4. 遵循现有架构模式（参考 `customer_app_service.py`）

---

## 重构步骤

### 步骤 1: 创建 `AIChatApplicationService`

**文件**: `app/application/ai_chat_app_service.py`

**职责**:
- 编排 AI 聊天业务逻辑
- 处理 `source=pro` 的即时工具执行（products/customers 查询）
- 处理普通聊天的即时工具执行（shipment_generate/shipments 查询）
- 统一响应格式构建

**主要方法**:
- `process_chat()` - 处理聊天主流程
- `execute_tool_instantly()` - 即时执行工具并返回结果
- `build_response()` - 统一响应格式构建

---

### 步骤 2: 创建 `FileAnalysisService`

**文件**: `app/application/file_analysis_app_service.py`

**职责**:
- 文件类型识别（通过扩展名和 SQLite 文件头）
- SQLite .db 文件分析
- 返回分析结果和建议用途

**主要方法**:
- `analyze_file()` - 分析上传文件
- `_identify_sqlite_db()` - 识别 SQLite 数据库
- `_extract_db_metadata()` - 提取数据库元数据

---

### 步骤 3: 创建 `UnitProductsImportService`

**文件**: `app/application/unit_products_import_app_service.py`

**职责**:
- 从上传的 SQLite .db 导入购买单位
- 导入该单位的产品列表
- 去重处理

**主要方法**:
- `import_unit_products()` - 执行导入
- `_read_source_products()` - 读取源 products 表
- `_ensure_unit_exists()` - 确保购买单位存在
- `_deduplicate_products()` - 产品去重
- `_batch_import_products()` - 批量导入产品

---

### 步骤 4: 在 `bootstrap.py` 中注册新服务

在 `app/bootstrap.py` 添加：
```python
@lru_cache(maxsize=1)
def get_ai_chat_app_service() -> AIChatApplicationService:
    return AIChatApplicationService()

@lru_cache(maxsize=1)
def get_file_analysis_service() -> FileAnalysisService:
    return FileAnalysisService()

@lru_cache(maxsize=1)
def get_unit_products_import_service() -> UnitProductsImportService:
    return UnitProductsImportService()
```

---

### 步骤 5: 简化 `ai_chat.py` 路由层

**重构后职责**:
- 路由定义和请求解析
- 调用 Application Service
- 响应组装
- 路由参数验证

**保留内容**:
- `TOOL_KEYWORDS_MAP` - 工具关键词映射
- `get_ai_service()` - 获取 AI 服务（保留因为 Service 内部使用）
- `set_file_pending_confirmation()` - 设置待确认上下文
- `recognize_intents()` - 意图识别函数
- 路由端点定义（但简化处理函数）

**需要简化的路由处理函数**:
1. `chat()` - 核心聊天接口
2. `chat_unified()` - 统一聊天接口（委托给 chat()）
3. `file_analyze()` - 文件分析接口
4. `import_unit_products()` - 产品导入接口

---

## 重构后结构

```
app/
├── application/
│   ├── ai_chat_app_service.py          # 新增：AI 聊天业务编排
│   ├── file_analysis_app_service.py    # 新增：文件分析业务
│   ├── unit_products_import_app_service.py  # 新增：产品导入业务
│   └── customer_app_service.py          # 现有：客户管理
│
├── routes/
│   └── ai_chat.py                       # 重构后：简化路由层 (~300 行)
│
└── bootstrap.py                         # 更新：注册新服务
```

---

## 实施顺序

1. 创建 `FileAnalysisService` (相对独立)
2. 创建 `UnitProductsImportService`
3. 创建 `AIChatApplicationService` (依赖前两个)
4. 更新 `bootstrap.py` 注册服务
5. 重构 `ai_chat.py` 路由层
6. 测试验证

---

## 风险控制

1. **向后兼容** - 保持 API 响应格式不变
2. **逐步迁移** - 先创建新 Service，路由层逐步切换调用
3. **保留原逻辑** - 重构初期保留原有代码作为参考
4. **测试覆盖** - 利用现有 `test_routes/test_ai_chat.py` 验证