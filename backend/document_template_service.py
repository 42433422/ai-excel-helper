"""
PostgreSQL ``document_templates``：业务导出模板元数据（Word / Excel）+ 磁盘路径解析。

- ``role``：price_list_docx | sales_contract_docx（销售合同可为 ``.docx`` 或 ``.xls/.xlsx``，由 ``file_format`` / 扩展名区分）
- ``slug``：稳定 id，供 API / 前端传递（与旧字段名 template_id 对齐）
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

ROLE_PRICE_LIST = "price_list_docx"
ROLE_SALES_CONTRACT = "sales_contract_docx"

# PostgreSQL：按路径扩展名把 Excel 模板排在 Word 之前（与 file_format 列是否陈旧无关）
_PG_ORDER_EXCEL_FIRST = (
    r"(CASE WHEN storage_relpath ~* '\.(xls|xlsx|xlsm)$' THEN 0 ELSE 1 END), sort_order, display_name"
)


def fhd_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _workspace_root() -> Path | None:
    w = (os.environ.get("WORKSPACE_ROOT") or "").strip()
    if not w:
        return None
    p = Path(w).expanduser()
    return p if p.is_dir() else None


def _mods_document_templates_rel(rel: str) -> bool:
    """``mods/<mod_id>/document_templates/...``，文件位于 XCAGI 根下（与 manifest 目录一致）。"""
    p = Path(rel.replace("\\", "/"))
    if ".." in p.parts or p.is_absolute():
        return False
    parts = p.parts
    if len(parts) < 4:
        return False
    if parts[0] != "mods":
        return False
    if parts[2] != "document_templates":
        return False
    return True


def _relpath_parts_ok(rel: str) -> bool:
    p = Path(rel.replace("\\", "/"))
    if ".." in p.parts or p.is_absolute():
        return False
    parts = p.parts
    if not parts:
        return False
    if parts[0] == "424":
        return True
    if parts[0] == "uploads" and len(parts) >= 3 and parts[1] == "document_templates":
        return True
    return _mods_document_templates_rel(rel)


def _resolve_storage_to_path(storage_relpath: str) -> Path | None:
    rel = (storage_relpath or "").strip().replace("\\", "/")
    if not rel or not _relpath_parts_ok(rel):
        return None
    repo = fhd_repo_root()
    if rel.startswith("424/"):
        p = (repo / rel).resolve()
        try:
            p.relative_to(repo.resolve())
        except ValueError:
            return None
        return p if p.is_file() else None
    if rel.startswith("uploads/document_templates/"):
        ws = _workspace_root()
        if ws is None:
            return None
        p = (ws / rel).resolve()
        try:
            p.relative_to(ws.resolve())
        except ValueError:
            return None
        return p if p.is_file() else None
    if rel.startswith("mods/"):
        try:
            from backend.shell.xcagi_mods_discover import xcagi_root
        except ImportError:
            return None
        root = xcagi_root()
        if root is None:
            return None
        p = (root / rel).resolve()
        try:
            p.relative_to(root.resolve())
        except ValueError:
            return None
        return p if p.is_file() else None
    return None


def _fallback_price_list_path() -> Path | None:
    env = (os.environ.get("FHD_PRICE_LIST_DOCX_TEMPLATE") or "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p
    for rel in (
        "424/document_templates/price_list_default.docx",
        "424/模板.docx",
    ):
        p = (fhd_repo_root() / rel).resolve()
        if p.is_file():
            return p
    return None


def _fallback_sales_contract_path() -> Path | None:
    env = (os.environ.get("FHD_SALES_CONTRACT_TEMPLATE") or "").strip()
    if env:
        p = Path(env).expanduser()
        if p.is_file():
            return p
    for rel in (
        "424/document_templates/送货单.xls",
        "424/document_templates/送货单.xlsx",
        "424/送货单.xls",
        "424/送货单.xlsx",
        "424/送货单1.xlsx",
    ):
        p = (fhd_repo_root() / rel).resolve()
        if p.is_file():
            return p
    return None


def resolve_sales_delivery_excel_template_with_meta() -> tuple[Path | None, str | None]:
    """
    销售合同 Excel 填充所用源文件（送货单版式）。

    仅匹配 ``slug=sales_delivery`` 且磁盘文件为 ``.xls/.xlsx/.xlsm``，再降级到仓库内送货单或
    环境变量 ``FHD_SALES_CONTRACT_TEMPLATE``（**仅当**指向电子表格）。

    不可复用 ``resolve_template_path_with_meta(slug='sales_delivery')``：当库中无该行时，
    后者会回落到 ``is_default`` / 任意 ``sales_contract_docx`` 行，易误选 **Word .docx**，
    进而触发 ``不支持的合同模板格式: .docx``。
    """
    from backend.sales_contract_excel_generate import is_sales_contract_excel_template_readable

    slug_target = "sales_delivery"
    try:
        from sqlalchemy import inspect, text

        from backend.database import get_sync_engine

        eng = get_sync_engine()
        insp = inspect(eng)
        if "document_templates" in insp.get_table_names():
            with eng.connect() as conn:
                row = conn.execute(
                    text(
                        "SELECT slug, storage_relpath FROM document_templates "
                        "WHERE role = :role AND slug = :slug AND is_active = true"
                    ),
                    {"role": ROLE_SALES_CONTRACT, "slug": slug_target},
                ).mappings().first()
                if row:
                    p = _resolve_storage_to_path(str(row["storage_relpath"] or ""))
                    if (
                        p is not None
                        and p.suffix.lower() in (".xls", ".xlsx", ".xlsm")
                        and is_sales_contract_excel_template_readable(p)
                    ):
                        return p, str(row["slug"] or slug_target)
    except Exception as e:
        logger.warning("resolve_sales_delivery_excel_template_with_meta PG: %s", e)

    env = (os.environ.get("FHD_SALES_CONTRACT_TEMPLATE") or "").strip()
    if env:
        p = Path(env).expanduser()
        if (
            p.is_file()
            and p.suffix.lower() in (".xls", ".xlsx", ".xlsm")
            and is_sales_contract_excel_template_readable(p)
        ):
            return p, "env"

    for rel in (
        "424/document_templates/送货单.xls",
        "424/document_templates/送货单.xlsx",
        "424/送货单.xls",
        "424/送货单.xlsx",
        "424/送货单1.xlsx",
    ):
        cand = (fhd_repo_root() / rel).resolve()
        if cand.is_file() and is_sales_contract_excel_template_readable(cand):
            return cand, "fallback"

    return None, None


def list_templates(role: str | None = None, kind: str | None = None) -> list[dict[str, Any]]:
    """列出激活模板行；``role`` 为 None 时返回全部。``kind=word|excel`` 仅筛选 ``excel_export`` 的文件格式。"""
    rows: list[dict[str, Any]] = []
    try:
        from backend.shell.mod_business_scope import business_data_exposed

        if not business_data_exposed():
            return rows

        from sqlalchemy import inspect, text

        from backend.database import get_sync_engine

        eng = get_sync_engine()
        insp = inspect(eng)
        if "document_templates" not in insp.get_table_names():
            return rows
        sql = (
            "SELECT slug, display_name, role, is_default, sort_order, storage_relpath, file_format "
            "FROM document_templates WHERE is_active = true"
        )
        params: dict[str, object] = {}
        if role:
            sql += " AND role = :role"
            params["role"] = role
        k = (kind or "").strip().lower()
        if k == "excel":
            sql += " AND file_format IN ('xls', 'xlsx', 'xlsm')"
        elif k == "word":
            sql += " AND file_format = 'docx'"
        sql += f" ORDER BY role, {_PG_ORDER_EXCEL_FIRST}"
        with eng.connect() as conn:
            for r in conn.execute(text(sql), params).mappings().all():
                rows.append(
                    {
                        "slug": str(r["slug"]),
                        "display_name": str(r["display_name"]),
                        "role": str(r["role"]),
                        "is_default": bool(r["is_default"]),
                        "sort_order": int(r["sort_order"] or 0),
                        "storage_relpath": str(r["storage_relpath"]),
                        "file_format": str(r.get("file_format") or "docx"),
                    }
                )
    except Exception as e:
        logger.warning("document_template_service.list_templates: %s", e)
    return rows


def resolve_template_path_with_meta(*, role: str, slug: str | None) -> tuple[Path | None, str | None]:
    """
    返回 ``(磁盘路径, 实际使用的 slug)``；降级成功时 slug 为 ``"env"`` 或 ``"fallback"``。

    未传 ``slug`` 时：在 ``is_default`` / 全量候选行中优先选 ``storage_relpath`` 为 ``.xls/.xlsx/.xlsm`` 的行，
    避免库中仍把 Word 标为默认或排序靠前时误生成 ``.docx``。
    """
    role = (role or "").strip()
    slug = (slug or "").strip() or None

    try:
        from sqlalchemy import inspect, text

        from backend.database import get_sync_engine

        eng = get_sync_engine()
        insp = inspect(eng)
        if "document_templates" in insp.get_table_names():
            with eng.connect() as conn:
                row = None
                if slug:
                    row = conn.execute(
                        text(
                            "SELECT slug, storage_relpath FROM document_templates "
                            "WHERE role = :role AND slug = :slug AND is_active = true"
                        ),
                        {"role": role, "slug": slug},
                    ).mappings().first()
                if row is None:
                    row = conn.execute(
                        text(
                            "SELECT slug, storage_relpath FROM document_templates "
                            "WHERE role = :role AND is_default = true AND is_active = true "
                            f"ORDER BY {_PG_ORDER_EXCEL_FIRST} LIMIT 1"
                        ),
                        {"role": role},
                    ).mappings().first()
                if row is None:
                    row = conn.execute(
                        text(
                            "SELECT slug, storage_relpath FROM document_templates "
                            "WHERE role = :role AND is_active = true "
                            f"ORDER BY {_PG_ORDER_EXCEL_FIRST} LIMIT 1"
                        ),
                        {"role": role},
                    ).mappings().first()
                if row:
                    p = _resolve_storage_to_path(str(row["storage_relpath"] or ""))
                    if p is not None:
                        return p, str(row["slug"] or "") or None
    except Exception as e:
        logger.warning("document_template_service.resolve_template_path_with_meta PG: %s", e)

    logger.warning(
        "document_template_service: PG 无可用模板 role=%s slug=%s，使用内置降级",
        role,
        slug,
    )
    if role == ROLE_PRICE_LIST:
        fp = _fallback_price_list_path()
        if not fp:
            return None, None
        env = (os.environ.get("FHD_PRICE_LIST_DOCX_TEMPLATE") or "").strip()
        try:
            if env and fp.resolve() == Path(env).expanduser().resolve():
                return fp, "env"
        except OSError:
            pass
        return fp, "fallback"
    if role == ROLE_SALES_CONTRACT:
        fp = _fallback_sales_contract_path()
        if not fp:
            return None, None
        env = (os.environ.get("FHD_SALES_CONTRACT_TEMPLATE") or "").strip()
        try:
            if env and fp.resolve() == Path(env).expanduser().resolve():
                return fp, "env"
        except OSError:
            pass
        return fp, "fallback"
    return None, None


def resolve_template_path(*, role: str, slug: str | None) -> Path | None:
    """仅返回路径；逻辑见 ``resolve_template_path_with_meta``。"""
    p, _ = resolve_template_path_with_meta(role=role, slug=slug)
    return p
