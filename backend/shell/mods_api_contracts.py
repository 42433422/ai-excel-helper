"""
XCAGI 壳层 Mod 相关 HTTP 契约说明（与仓库内测试、scripts/check_api_8000 对齐）。

仓库内无独立前端源码；下列字段以当前实现与 ``test_http_app`` 断言为准，
供后续改接口时做兼容检查。

列表数据可由 **MODstore** 生成静态文件 ``backend/shell/fhd_shell_mods.json``（见
``modman export-fhd-shell``）；未生成时由 ``mods_catalog`` 内置列表提供。

GET /api/mods, /api/mods/
    轮询: 无（按需拉取列表）。
    顶层: ``success`` (bool, 须为 True), ``data`` (list)。
    ``data[]`` 元素: ``id`` (str), ``name`` (str), ``type`` (str, 如 category|template),
    ``color`` (str | null), 可选 ``description`` (str)。
    扩展 manifest 还可选: ``shell_tagline``（侧栏副标题）、``shell_menu_preset``（侧栏菜单文案预设键）、
    ``library_blurb``（MODstore 库卡片一行说明）；见 ``xcagi_mods_discover.read_manifest_dicts``。
    数据库种子: ``database_seed_sql``（单文件）、``database_seed_files``（相对路径数组）、或嵌套
    ``database: { seed_files, notes_zh }``；执行与分库模型见 ``mod_database_gate`` 模块注释。

GET /api/mods/loading-status
    轮询: 旧版前端可能轮询直至 ``loaded`` 为 True；当前恒为就绪。
    顶层: ``success``, ``loading`` (bool), ``loaded`` (bool),
    ``data``: ``{ loading, loaded, status }``，其中 ``status`` 为 ``"ready"``。

GET /api/startup/status
    轮询: 启动阶段直至 ``ready`` 为 True（当前恒为就绪）。
    顶层: ``ready`` (bool), ``progress_percent`` (int),
    ``components`` (list of ``{ name, status }``)；须包含 ``name=="mods"`` 且 ``status=="ready"``。

GET /api/mods/routes
    动态路由表占位；``success`` + ``data`` (object, 当前为空 dict)。

GET /api/mods/{project_id}/{agent_name}/status
    代理状态轮询占位；``success`` + ``data``:
    ``agent_name``, ``project_id``, ``status`` (如 ready), ``loaded`` (bool), ``error`` (null)。

POST /api/state/client-mods-off
    Body JSON: ``client_mods_off`` (bool, 可缺省视为 false)。
    响应: ``success``, ``client_mods_off``（回显解析后的 bool）。
"""
