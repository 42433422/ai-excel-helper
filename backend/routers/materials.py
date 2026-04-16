"""
原材料仓库 API 路由：提供原材料的 CRUD 操作（PostgreSQL / DATABASE_URL）。
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query

from backend.database import get_sync_engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["materials"])


def _materials_pg_engine_insp():
    from sqlalchemy import inspect

    eng = get_sync_engine()
    insp = inspect(eng)
    if "materials" not in insp.get_table_names():
        raise HTTPException(status_code=503, detail="PostgreSQL 库中缺少 materials 表。")
    return eng, insp


def _material_row_to_dict(row: Mapping[str, Any]) -> dict[str, Any]:
    d = dict(row)
    ia = d.get("is_active")
    return {
        "id": d["id"],
        "code": d.get("material_code"),
        "name": d.get("name"),
        "category": d.get("category"),
        "spec": d.get("specification"),
        "unit": d.get("unit"),
        "quantity": d.get("quantity") or 0,
        "price": d.get("unit_price"),
        "supplier": d.get("supplier"),
        "warehouse_location": d.get("warehouse_location"),
        "min_stock": d.get("min_stock"),
        "max_stock": d.get("max_stock"),
        "description": d.get("description"),
        "is_active": bool(ia) if ia is not None else True,
        "created_at": d.get("created_at"),
        "updated_at": d.get("updated_at"),
    }


def _pg_active_clause() -> str:
    return "(is_active IS NULL OR CAST(is_active AS INTEGER) = 1)"


def _pg_inactive_value(insp) -> Any:
    for c in insp.get_columns("materials"):
        if c["name"] == "is_active":
            t = str(c.get("type") or "").lower()
            return False if "bool" in t else 0
    return 0


def _materials_list_pg(
    search: str | None, category: str | None
) -> tuple[list[dict[str, Any]], list[str]]:
    from sqlalchemy import text

    eng, _insp = _materials_pg_engine_insp()
    where = [_pg_active_clause()]
    params: dict[str, Any] = {}
    if search:
        where.append(
            "(CAST(name AS TEXT) ILIKE :sp OR CAST(material_code AS TEXT) ILIKE :sp "
            "OR CAST(category AS TEXT) ILIKE :sp)"
        )
        params["sp"] = f"%{search.strip()}%"
    if category:
        where.append("category = :cat")
        params["cat"] = category
    where_sql = " AND ".join(where)
    sql = f"SELECT * FROM materials WHERE {where_sql} ORDER BY id DESC"
    with eng.connect() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
        materials = [_material_row_to_dict(dict(r)) for r in rows]
        categories: list[str] = []
        if not search and not category:
            crows = conn.execute(
                text(
                    "SELECT DISTINCT category FROM materials WHERE category IS NOT NULL "
                    "AND CAST(category AS TEXT) != '' ORDER BY category"
                )
            ).fetchall()
            categories = [row[0] for row in crows if row[0]]
    return materials, categories


@router.get("/materials")
async def materials_list(
    search: str | None = Query(None),
    category: str | None = Query(None),
) -> dict:
    """
    获取原材料列表，支持搜索和分类过滤。

    - **search**: 搜索关键词（名称、编码、分类）
    - **category**: 分类过滤
    """
    materials, categories = _materials_list_pg(search, category)
    return {
        "success": True,
        "data": materials,
        "categories": categories,
    }


@router.get("/materials/{material_id}")
async def materials_get(material_id: int) -> dict:
    """获取单个原材料详情。"""
    from sqlalchemy import text

    eng, _insp = _materials_pg_engine_insp()
    with eng.connect() as conn:
        r = conn.execute(
            text("SELECT * FROM materials WHERE id = :id"),
            {"id": material_id},
        ).mappings().first()
    if not r:
        raise HTTPException(status_code=404, detail="原材料不存在")
    return {"success": True, "data": _material_row_to_dict(dict(r))}


@router.post("/materials")
async def materials_create(body: dict = Body(default_factory=dict)) -> dict:
    """创建新的原材料。"""
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="原材料名称不能为空")
    code = body.get("code", "").strip() or None
    cat = body.get("category", "").strip() or None
    spec = body.get("spec", "").strip() or None
    unit = body.get("unit", "个").strip()
    quantity = float(body.get("quantity", 0) or 0)
    price = body.get("price")
    supplier = body.get("supplier", "").strip() or None
    warehouse_location = body.get("warehouse_location", "").strip() or None
    min_stock = body.get("min_stock")
    max_stock = body.get("max_stock")
    description = body.get("description", "").strip() or None
    now = datetime.now().isoformat()

    from sqlalchemy import text

    eng, _insp = _materials_pg_engine_insp()
    with eng.begin() as conn:
        r = conn.execute(
            text(
                """
                INSERT INTO materials (
                    material_code, name, category, specification, unit,
                    quantity, unit_price, supplier, warehouse_location,
                    min_stock, max_stock, description, is_active,
                    created_at, updated_at
                ) VALUES (
                    :code, :name, :cat, :spec, :unit,
                    :qty, :price, :sup, :wh,
                    :min_s, :max_s, :desc, 1,
                    :ca, :ua
                )
                RETURNING id
                """
            ),
            {
                "code": code,
                "name": name,
                "cat": cat,
                "spec": spec,
                "unit": unit,
                "qty": quantity,
                "price": price,
                "sup": supplier,
                "wh": warehouse_location,
                "min_s": min_stock,
                "max_s": max_stock,
                "desc": description,
                "ca": now,
                "ua": now,
            },
        )
        mid = int(r.scalar_one())
    with eng.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM materials WHERE id = :id"), {"id": mid}
        ).mappings().first()
    return {
        "success": True,
        "data": _material_row_to_dict(dict(row)),
        "message": "原材料添加成功",
    }


@router.put("/materials/{material_id}")
async def materials_update(material_id: int, body: dict = Body(default_factory=dict)) -> dict:
    """更新原材料信息。"""
    name = body.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="原材料名称不能为空")
    code = body.get("code", "").strip() or None
    cat = body.get("category", "").strip() or None
    spec = body.get("spec", "").strip() or None
    unit = body.get("unit", "个").strip()
    quantity = float(body.get("quantity", 0) or 0)
    price = body.get("price")
    supplier = body.get("supplier", "").strip() or None
    warehouse_location = body.get("warehouse_location", "").strip() or None
    min_stock = body.get("min_stock")
    max_stock = body.get("max_stock")
    description = body.get("description", "").strip() or None
    is_active = body.get("is_active", True)
    now = datetime.now().isoformat()

    from sqlalchemy import text

    eng, insp = _materials_pg_engine_insp()
    ia_val: Any = 1 if is_active else 0
    for c in insp.get_columns("materials"):
        if c["name"] == "is_active":
            t = str(c.get("type") or "").lower()
            ia_val = bool(is_active) if "bool" in t else (1 if is_active else 0)
            break
    with eng.begin() as conn:
        r = conn.execute(
            text("SELECT id FROM materials WHERE id = :id"), {"id": material_id}
        ).first()
        if not r:
            raise HTTPException(status_code=404, detail="原材料不存在")
        conn.execute(
            text(
                """
                UPDATE materials SET
                    material_code = :code,
                    name = :name,
                    category = :cat,
                    specification = :spec,
                    unit = :unit,
                    quantity = :qty,
                    unit_price = :price,
                    supplier = :sup,
                    warehouse_location = :wh,
                    min_stock = :min_s,
                    max_stock = :max_s,
                    description = :desc,
                    is_active = :ia,
                    updated_at = :ua
                WHERE id = :id
                """
            ),
            {
                "code": code,
                "name": name,
                "cat": cat,
                "spec": spec,
                "unit": unit,
                "qty": quantity,
                "price": price,
                "sup": supplier,
                "wh": warehouse_location,
                "min_s": min_stock,
                "max_s": max_stock,
                "desc": description,
                "ia": ia_val,
                "ua": now,
                "id": material_id,
            },
        )
    with eng.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM materials WHERE id = :id"), {"id": material_id}
        ).mappings().first()
    return {
        "success": True,
        "data": _material_row_to_dict(dict(row)),
        "message": "原材料更新成功",
    }


@router.delete("/materials/{material_id}")
async def materials_delete(material_id: int) -> dict:
    """删除原材料（软删除）。"""
    now = datetime.now().isoformat()
    from sqlalchemy import text

    eng, insp = _materials_pg_engine_insp()
    inv = _pg_inactive_value(insp)
    with eng.begin() as conn:
        r = conn.execute(
            text("SELECT id FROM materials WHERE id = :id"), {"id": material_id}
        ).first()
        if not r:
            raise HTTPException(status_code=404, detail="原材料不存在")
        conn.execute(
            text(
                "UPDATE materials SET is_active = :inv, updated_at = :ua WHERE id = :id"
            ),
            {"inv": inv, "ua": now, "id": material_id},
        )
    return {"success": True, "message": "原材料已删除"}


@router.get("/materials/low-stock")
async def materials_low_stock() -> dict:
    """获取库存低于最小库存的原材料列表。"""
    from sqlalchemy import text

    eng, _insp = _materials_pg_engine_insp()
    sql = f"""
        SELECT * FROM materials
        WHERE {_pg_active_clause()}
        AND min_stock IS NOT NULL
        AND quantity < min_stock
        ORDER BY quantity ASC
    """
    with eng.connect() as conn:
        rows = conn.execute(text(sql)).mappings().all()
    return {
        "success": True,
        "data": [_material_row_to_dict(dict(r)) for r in rows],
    }
