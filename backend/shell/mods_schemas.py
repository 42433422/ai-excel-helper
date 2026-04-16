"""Pydantic 模型：XCAGI 壳层 /api/mods* 等与 OpenAPI 契约。"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class ModItem(BaseModel):
    """单条 mod / 模板目录项（与历史 JSON 形状一致）。"""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    type: str = "mod"
    color: str | None = None
    description: str | None = None
    #: 可选：PostgreSQL 种子 SQL 单文件路径（manifest 中常为相对 mod 目录；扫描后多为绝对路径）
    database_seed_sql: str | None = None
    #: 磁盘扩展 manifest 常见字段（XCAGI 前端侧栏 / 工作流用）
    version: str | None = None
    author: str | None = None
    primary: bool | None = None
    menu: list[dict[str, Any]] | None = None
    #: manifest.workflow_employees；副窗「工作流员工」与任务面板依赖此字段
    workflow_employees: list[dict[str, Any]] | None = None
    #: 宿主侧栏「AI 智能助手」下小字；不填则前端用默认「出货单管理系统」
    shell_tagline: str | None = None
    #: 侧栏内置菜单文案预设键（与 XCAGI Sidebar 中 industryMenuNameMap 一致，如 涂料、员工管理、通用）
    shell_menu_preset: str | None = None
    #: MODstore 库卡片副标题一行；不填可仍用 description
    library_blurb: str | None = None
    #: manifest.database.seed_files 或顶层 database_seed_files：相对 mod 目录的 .sql 列表，门禁通过后按顺序执行
    database_seed_files: list[str] | None = None
    #: manifest.database.notes_zh / database_notes：说明本 Mod 期望的库形态、与宿主 core 表关系等（仅展示）
    database_notes: str | None = None


class ModsListResponse(BaseModel):
    success: Literal[True] = True
    data: list[ModItem]


class ModsLoadingPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    loading: bool = False
    loaded: bool = True
    status: Literal["ready"] = "ready"
    discovered_mod_ids: list[str] = Field(default_factory=list)
    mods: list[dict[str, Any]] = Field(default_factory=list)
    mods_loaded: int = 0
    load_mismatch: bool = False
    mods_disabled: bool = False
    #: 与 manifest ``primary: true`` 一致；仅当恰好一个主 Mod 时非空
    primary_mod_id: str | None = None
    primary_mod_name: str | None = None
    primary_mod_count: int = 0


class ModsLoadingStatusResponse(BaseModel):
    success: Literal[True] = True
    loading: bool = False
    loaded: bool = True
    data: ModsLoadingPayload = Field(default_factory=ModsLoadingPayload)


class StartupComponent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str
    status: str


class StartupStatusResponse(BaseModel):
    ready: bool = True
    progress_percent: int = 100
    components: list[StartupComponent]


class ModsRoutesResponse(BaseModel):
    success: Literal[True] = True
    #: 与前端 ``registerModRoutes`` 一致：``{ mod_id, routes_path }[]``
    data: list[dict[str, Any]] = Field(default_factory=list)


class ModAgentStatusData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    agent_name: str
    project_id: str
    status: str = "ready"
    loaded: bool = True
    error: str | None = None


class ModAgentStatusResponse(BaseModel):
    success: Literal[True] = True
    data: ModAgentStatusData


class ClientModsOffRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    client_mods_off: bool | None = None


class ClientModsOffResponse(BaseModel):
    success: Literal[True] = True
    client_mods_off: bool
