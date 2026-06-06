"""太阳鸟 PRO — FastAPI 路由（考勤等）；无 Flask 依赖。"""

from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, Body, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse

logger = logging.getLogger(__name__)
DEFAULT_TEMPLATE_RELPATH = "424/考勤-2026-3月份考勤统计表.xlsx"


def _load_products_personnel_roster_from_host() -> list[tuple[str, str, str]]:
    """主应用「人员管理」同一套 Product 表（model 为 app.db.models.product.Product）。"""
    try:
        from app.db.models.product import Product
        from app.db.session import get_db
    except Exception:
        return []
    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    try:
        with get_db() as db:
            q = db.query(Product).filter(Product.is_active == 1).order_by(Product.id)
            for p in q:
                name = (getattr(p, "name", None) or "").strip()
                if not name or name in seen:
                    continue
                seen.add(name)
                dept = (getattr(p, "unit", None) or "").strip()
                spec = (getattr(p, "specification", None) or "").strip()
                out.append((dept, spec, name))
    except Exception:
        logger.exception("读取主库人员(products)失败")
        return []
    return out


def _resolve_personnel_roster(db_path: Path) -> list[tuple[str, str, str]]:
    host = _load_products_personnel_roster_from_host()
    if host:
        return host
    return _load_products_personnel_roster(db_path)


def _load_products_personnel_roster(db_path: Path) -> list[tuple[str, str, str]]:
    """侧栏「人员管理」对应 ``products`` 表：(部门/单位列, 规格/性质列, 姓名)，按 id 顺序、姓名去重。"""
    import sqlite3

    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT unit, specification, name FROM products "
            "WHERE name IS NOT NULL AND TRIM(name) != '' ORDER BY id"
        )
    except sqlite3.Error:
        conn.close()
        return []
    seen: set[str] = set()
    out: list[tuple[str, str, str]] = []
    for row in cur.fetchall():
        name = str(row["name"]).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        dept = str(row["unit"] or "").strip()
        nature = str(row["specification"] or "").strip()
        out.append((dept, nature, name))
    conn.close()
    return out


def _normalize_relpath(raw: str, *, field_name: str) -> str:
    rel = unquote(raw or "").strip().replace("\\", "/").lstrip("/")
    if not rel:
        raise ValueError(f"missing {field_name}")
    return rel


def register_fastapi_routes(app, mod_id: str) -> None:
    """在 FastAPI 上注册示例 hello 与考勤接口。"""
    # 考勤转换的实现放在 mod 私有包 ``taiyangniao_attendance/``
    # （被 mod_manager 加到 sys.path 的 ``backend/`` 可直接绝对 import）。
    from taiyangniao_attendance.convert import convert_attendance_file
    from app.mod_sdk.workspace import resolve_safe_workspace_relpath

    # import_mod_backend_py 以独立模块名加载本文件时无包上下文，相对导入会失败。
    try:
        from .database import get_database_path
    except ImportError:
        import sys
        from pathlib import Path

        _backend_dir = str(Path(__file__).resolve().parent)
        if _backend_dir not in sys.path:
            sys.path.insert(0, _backend_dir)
        from database import get_database_path

    router = APIRouter(tags=[f"mod-{mod_id}"])

    @router.get("/hello")
    async def hello():
        return {
            "success": True,
            "data": {"message": f"Hello from {mod_id}", "mod": "taiyangniao-pro"},
        }

    @router.get("/attendance/policy")
    async def attendance_policy_get() -> dict:
        """太阳鸟考勤裁窗配置（读写 approval_config.yaml 的 attendance_policy 段）。"""
        try:
            from resources.config.approval_config import get_approval_config

            pol = getattr(get_approval_config(), "attendance_policy", None) or {}
        except Exception as exc:
            logger.exception("读取考勤策略失败")
            return JSONResponse(
                {"success": False, "message": str(exc)},
                status_code=500,
            )
        return {"success": True, "attendance_policy": pol}

    @router.post("/attendance/policy")
    async def attendance_policy_post(body: dict = Body(default_factory=dict)) -> dict:
        payload = body if isinstance(body, dict) else {}
        raw = payload.get("attendance_policy")
        if not isinstance(raw, dict):
            return JSONResponse(
                {"success": False, "message": "请提供 attendance_policy 对象"},
                status_code=400,
            )
        try:
            from resources.config.approval_config import (
                get_approval_config,
                normalize_attendance_policy,
                reload_approval_config,
            )

            config = get_approval_config()
            config.attendance_policy = normalize_attendance_policy(raw)
            config.save()
            reload_approval_config()
            return {
                "success": True,
                "message": "考勤规则已保存",
                "attendance_policy": config.attendance_policy,
            }
        except Exception as exc:
            logger.exception("保存考勤策略失败")
            return JSONResponse(
                {"success": False, "message": str(exc)},
                status_code=500,
            )

    @router.get("/attendance/rules")
    async def attendance_rules() -> dict:
        lines = [
            "优先读取钉钉「每日统计」，再用「原始记录」补充打卡时间与去重。",
            "重复打卡按上午/下午/晚上分段去重，优先保留每段的有效边界打卡。",
            "目标文件会在固定模板基础上回填「明细」工作表。",
            "周一到周六正班固定为 08:00-12:00、13:30-17:30；周日算加班。",
        ]
        config = {
            "default_header_row": 0,
            "default_output_relpath": "424/考勤转换输出.xlsx",
            "accepted_extensions": [".xlsx", ".xlsm", ".xls"],
            "allow_template_append": True,
            "default_template_relpath": DEFAULT_TEMPLATE_RELPATH,
            "default_template_behavior": "固定模板版式；勾选按人员管理名单时用 products 重排明细，钉钉按名回填，无则空",
        }
        schedule_groups = [
            {
                "name": "公司-考勤 / 公司正班",
                "headcount": "按导出表统计",
                "shift_type": "固定班制",
                "lines": [
                    "周一到周六：正班固定 08:00-12:00 / 13:30-17:30",
                    "晚上：18:00 后按最后一次打卡计加班",
                    "周日：全部按星期天加班处理",
                ],
            },
            {
                "name": "惠州工厂-正班 / 工厂正班",
                "headcount": "按导出表统计",
                "shift_type": "固定班制",
                "lines": [
                    "周一到周六：正班固定 08:00-12:00 / 13:30-17:30",
                    "晚上：18:00 后按最后一次打卡计加班",
                    "周日：全部按星期天加班处理",
                ],
            }
        ]
        return {
            "success": True,
            "data": {
                "lines": lines,
                "saturday_window_label": "13:30 - 16:00",
                "config": config,
                "schedule_groups": schedule_groups,
            },
        }

    @router.post("/attendance/convert-upload", response_model=None)
    async def attendance_convert_upload(
        file: UploadFile = File(...),
        output_relpath: str = Form("424/考勤转换输出.xlsx"),
        template_relpath: str = Form(DEFAULT_TEMPLATE_RELPATH),
        month: str = Form(""),
        header_row: int = Form(0),
        use_llm: str = Form(""),
        use_personnel_roster: str = Form("1"),
    ):
        if not file.filename:
            return JSONResponse(
                {"success": False, "error": "missing file name"},
                status_code=400,
            )
        suffix = Path(file.filename).suffix.lower()
        if suffix not in {".xlsx", ".xlsm", ".xls"}:
            return JSONResponse(
                {"success": False, "error": "unsupported file type"},
                status_code=400,
            )

        try:
            out_rel = _normalize_relpath(output_relpath, field_name="output_relpath")
        except ValueError as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=400)

        try:
            upload_dir = resolve_safe_workspace_relpath("uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)
            src_name = Path(file.filename).name or "attendance-upload.xlsx"
            src_path = upload_dir / src_name
            content = await file.read()
            with src_path.open("wb") as f:
                f.write(content)
        except Exception as e:
            logger.exception("Failed to save attendance upload")
            return JSONResponse(
                {"success": False, "error": f"save upload failed: {e}"},
                status_code=500,
            )

        try:
            out_path = resolve_safe_workspace_relpath(out_rel)
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=400)

        raw_tpl_rel = unquote(template_relpath or "").strip()
        if raw_tpl_rel:
            try:
                normalized_raw_tpl = _normalize_relpath(raw_tpl_rel, field_name="template_relpath")
            except ValueError as e:
                return JSONResponse({"success": False, "error": str(e)}, status_code=400)
            if normalized_raw_tpl != DEFAULT_TEMPLATE_RELPATH:
                return JSONResponse(
                    {"success": False, "error": f"请使用固定模板: {DEFAULT_TEMPLATE_RELPATH}"},
                    status_code=400,
                )

        tpl_rel = DEFAULT_TEMPLATE_RELPATH
        try:
            template_path = resolve_safe_workspace_relpath(tpl_rel)
            if not template_path.exists():
                return JSONResponse(
                    {"success": False, "error": f"模板文件不存在: {tpl_rel}"},
                    status_code=400,
                )
            if not template_path.is_file():
                return JSONResponse(
                    {"success": False, "error": f"模板路径不是文件: {tpl_rel}"},
                    status_code=400,
                )
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=400)

        out_path.parent.mkdir(parents=True, exist_ok=True)

        use_llm_flag = (unquote(use_llm or "").strip().lower()) in (
            "1", "true", "yes", "on",
        )
        use_pr = (unquote(use_personnel_roster or "").strip().lower()) in (
            "1",
            "true",
            "yes",
            "on",
        )
        roster: list[tuple[str, str, str]] | None = None
        if use_pr:
            roster = _resolve_personnel_roster(get_database_path())
            if not roster:
                return JSONResponse(
                    {
                        "success": False,
                        "error": "已勾选「按人员管理名单」，但主库「人员管理」与 mod 备用库均无人员。请先在侧栏「人员管理」导入或录入后再转换；或取消勾选改用模板内原名单。",
                    },
                    status_code=400,
                )

        try:
            result = convert_attendance_file(
                str(src_path),
                str(out_path),
                template_path=str(template_path),
                month=unquote(month or "").strip() or None,
                header_row=max(0, int(header_row)),
                use_llm=use_llm_flag or None,  # None -> 交给 env 开关决定
                personnel_roster=roster,
            )
        except Exception as e:
            logger.exception("Attendance conversion crashed")
            return JSONResponse(
                {"success": False, "error": f"convert failed: {e}"},
                status_code=500,
            )
        if not result.get("success"):
            return JSONResponse(
                {"success": False, "error": str(result.get("error") or "convert failed")},
                status_code=400,
            )

        rows_in = int(result.get("rows_in") or 0)
        rows_stats = int(result.get("rows_stats") or 0)
        if rows_in == 0:
            header_info = result.get("header_info") or {}
            msg = (
                "未从 ‘每日统计’ 工作表中解析到任何数据行。"
                "通常原因是表头行号与实际不符，或必需列缺失。"
                "可尝试：1) 填写正确的 ‘表头所在行’；2) 勾选 ‘启用 LLM 智能识别表头’ 重试。"
            )
            return JSONResponse(
                {
                    "success": False,
                    "error": msg,
                    "data": {
                        "rows_in": 0,
                        "rows_stats": rows_stats,
                        "header_info": header_info,
                        "used_llm": bool(result.get("used_llm")),
                    },
                },
                status_code=422,
            )

        src_display = result.get("input") or str(src_path)
        out_display = result.get("output") or str(out_path)
        mon = result.get("month") or unquote(month or "").strip()
        return {
            "success": True,
            "data": {
                "input_path": src_display,
                "output_path": out_display,
                "output_relpath": out_rel,
                "rows_in": rows_in,
                "rows_used_for_template": int(result.get("rows_used_for_template") or 0),
                "personnel_roster_count": int(result.get("personnel_roster_count") or 0),
                "rows_stats": rows_stats,
                "template_relpath": tpl_rel,
                "month": mon,
                "header_row": max(0, int(header_row)),
                "employees_total": int(result.get("employees_total") or 0),
                "employees_matched": int(result.get("employees_matched") or 0),
                "unmatched_names": result.get("unmatched_names") or [],
                "header_info": result.get("header_info"),
                "used_llm": bool(result.get("used_llm")),
                "output_sheet_names": result.get("output_sheet_names") or [],
            },
        }

    @router.get("/attendance/download", response_model=None)
    async def attendance_download(relpath: str):
        try:
            rel = _normalize_relpath(relpath, field_name="relpath")
            p = resolve_safe_workspace_relpath(rel)
        except ValueError as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=400)
        except Exception as e:
            return JSONResponse({"success": False, "error": str(e)}, status_code=400)

        if not p.exists() or not p.is_file():
            return JSONResponse({"success": False, "error": "file not found"}, status_code=404)

        return FileResponse(path=str(p), filename=p.name, media_type="application/octet-stream")

    @router.get("/employees", response_model=None)
    async def list_employees(page: int = 1, page_size: int = 50, search: str = ""):
        import sqlite3, math
        db_path = get_database_path()
        if not db_path.exists():
            return {"success": True, "data": {"items": [], "total": 0, "page": page, "page_size": page_size}}
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        like = f"%{search}%"
        cur.execute(
            "SELECT COUNT(*) FROM attendance_employees WHERE employee_name LIKE ? OR department LIKE ?",
            (like, like),
        )
        total = cur.fetchone()[0]
        offset = (page - 1) * page_size
        cur.execute(
            "SELECT id, employee_name, department, main_department, attendance_group, employee_no, position, user_id "
            "FROM attendance_employees WHERE employee_name LIKE ? OR department LIKE ? "
            "ORDER BY id LIMIT ? OFFSET ?",
            (like, like, page_size, offset),
        )
        items = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {"success": True, "data": {"items": items, "total": total, "page": page, "page_size": page_size}}

    @router.get("/departments", response_model=None)
    async def list_departments(page: int = 1, page_size: int = 50, search: str = ""):
        import sqlite3
        db_path = get_database_path()
        if not db_path.exists():
            return {"success": True, "data": {"items": [], "total": 0, "page": page, "page_size": page_size}}
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        like = f"%{search}%"
        cur.execute(
            "SELECT COUNT(*) FROM attendance_departments WHERE department LIKE ? OR main_department LIKE ?",
            (like, like),
        )
        total = cur.fetchone()[0]
        offset = (page - 1) * page_size
        cur.execute(
            "SELECT id, department, main_department, attendance_group "
            "FROM attendance_departments WHERE department LIKE ? OR main_department LIKE ? "
            "ORDER BY id LIMIT ? OFFSET ?",
            (like, like, page_size, offset),
        )
        items = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {"success": True, "data": {"items": items, "total": total, "page": page, "page_size": page_size}}

    @router.get("/products/list", response_model=None)
    async def products_list(
        page: int = 1,
        per_page: int = 20,
        keyword: str = "",
        unit: str = "",
    ):
        import sqlite3
        db_path = get_database_path()
        if not db_path.exists():
            return {"success": True, "data": [], "total": 0}
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cond = []
        args = []
        if keyword:
            cond.append("(model_number LIKE ? OR name LIKE ?)")
            args.extend([f"%{keyword}%", f"%{keyword}%"])
        if unit:
            cond.append("unit = ?")
            args.append(unit)
        where = " AND ".join(cond) if cond else "1=1"
        cur.execute(f"SELECT COUNT(*) FROM products WHERE {where}", args)
        total = cur.fetchone()[0]
        offset = (page - 1) * per_page
        cur.execute(
            f"SELECT id, model_number, name, specification, price, unit "
            f"FROM products WHERE {where} ORDER BY id LIMIT ? OFFSET ?",
            [*args, per_page, offset],
        )
        items = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {"success": True, "data": items, "total": total}

    @router.get("/products/{product_id}", response_model=None)
    async def products_get(product_id: int):
        import sqlite3
        db_path = get_database_path()
        if not db_path.exists():
            return JSONResponse({"success": False, "error": "not found"}, status_code=404)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return JSONResponse({"success": False, "error": "not found"}, status_code=404)
        return {"success": True, "data": dict(row)}

    @router.post("/products/add", response_model=None)
    async def products_add(data: dict):
        import sqlite3, datetime
        db_path = get_database_path()
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        now = datetime.datetime.now().isoformat()
        cur.execute(
            "INSERT INTO products (source_file, model_number, name, specification, price, unit, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                data.get("source_file", ""),
                data.get("model_number", ""),
                data.get("name", ""),
                data.get("specification", ""),
                float(data.get("price") or 0),
                data.get("unit", ""),
                now, now,
            ),
        )
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return {"success": True, "data": {"id": new_id}}

    @router.post("/products/update", response_model=None)
    async def products_update(data: dict):
        import sqlite3, datetime
        db_path = get_database_path()
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        now = datetime.datetime.now().isoformat()
        cur.execute(
            "UPDATE products SET model_number=?, name=?, specification=?, price=?, unit=?, updated_at=? WHERE id=?",
            (
                data.get("model_number", ""),
                data.get("name", ""),
                data.get("specification", ""),
                float(data.get("price") or 0),
                data.get("unit", ""),
                now,
                data.get("id"),
            ),
        )
        conn.commit()
        conn.close()
        return {"success": True}

    @router.post("/products/delete", response_model=None)
    async def products_delete(data: dict):
        import sqlite3
        db_path = get_database_path()
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("DELETE FROM products WHERE id = ?", (data.get("id"),))
        conn.commit()
        conn.close()
        return {"success": True}

    @router.post("/products/batch-delete", response_model=None)
    async def products_batch_delete(data: dict):
        import sqlite3
        ids = data.get("ids") or []
        if not ids:
            return {"success": True}
        db_path = get_database_path()
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        placeholders = ",".join("?" * len(ids))
        cur.execute(f"DELETE FROM products WHERE id IN ({placeholders})", ids)
        conn.commit()
        conn.close()
        return {"success": True}

    @router.get("/products/product_names", response_model=None)
    async def products_names():
        import sqlite3
        db_path = get_database_path()
        if not db_path.exists():
            return {"success": True, "data": []}
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, model_number, name FROM products ORDER BY id")
        items = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {"success": True, "data": items}

    @router.get("/products/product_names/search", response_model=None)
    async def products_names_search(keyword: str = ""):
        import sqlite3
        db_path = get_database_path()
        if not db_path.exists():
            return {"success": True, "data": []}
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT id, model_number, name FROM products WHERE model_number LIKE ? OR name LIKE ? LIMIT 20",
            (f"%{keyword}%", f"%{keyword}%"),
        )
        items = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {"success": True, "data": items}

    @router.post("/products/batch", response_model=None)
    async def products_batch_add(data: dict):
        import sqlite3, datetime
        products_list = data.get("products") or []
        if not products_list:
            return {"success": True, "data": []}
        db_path = get_database_path()
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        now = datetime.datetime.now().isoformat()
        rows = []
        for p in products_list:
            rows.append((
                "", p.get("model_number", ""), p.get("name", ""),
                p.get("specification", ""), float(p.get("price") or 0),
                p.get("unit", ""), now, now,
            ))
        cur.executemany(
            "INSERT INTO products (source_file, model_number, name, specification, price, unit, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
            rows,
        )
        conn.commit()
        conn.close()
        return {"success": True, "data": []}

    @router.get("/customers", response_model=None)
    @router.get("/customers/", response_model=None)
    async def customers_all(page: int = 1, per_page: int = 20, keyword: str = ""):
        return await customers_list(page=page, per_page=per_page, keyword=keyword)

    @router.get("/customers/list", response_model=None)
    async def customers_list(
        page: int = 1,
        per_page: int = 20,
        keyword: str = "",
        purchase_unit: str = "",
    ):
        import sqlite3
        db_path = get_database_path()
        if not db_path.exists():
            return {"success": True, "data": [], "total": 0}
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cond = []
        args = []
        if keyword:
            cond.append("(customer_name LIKE ? OR contact_person LIKE ? OR contact_phone LIKE ?)")
            args.extend([f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"])
        if purchase_unit:
            cond.append("purchase_unit = ?")
            args.append(purchase_unit)
        where = " AND ".join(cond) if cond else "1=1"
        cur.execute(f"SELECT COUNT(*) FROM customers WHERE {where}", args)
        total = cur.fetchone()[0]
        offset = (page - 1) * per_page
        cur.execute(
            f"SELECT id, customer_name, contact_person, contact_phone, address, purchase_unit "
            f"FROM customers WHERE {where} ORDER BY id LIMIT ? OFFSET ?",
            [*args, per_page, offset],
        )
        items = [dict(r) for r in cur.fetchall()]
        conn.close()
        return {"success": True, "data": items, "total": total}

    def _distinct_customer_purchase_units() -> list[str]:
        import sqlite3

        db_path = get_database_path()
        if not db_path.exists():
            return []
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT TRIM(purchase_unit) FROM customers "
            "WHERE purchase_unit IS NOT NULL AND TRIM(purchase_unit) != '' "
            "ORDER BY purchase_unit COLLATE NOCASE"
        )
        units = [str(row[0]).strip() for row in cur.fetchall() if row and str(row[0]).strip()]
        conn.close()
        return units

    @router.get("/purchase_units")
    @router.get("/purchase_units/")
    async def purchase_units_list():
        units = _distinct_customer_purchase_units()
        return {"success": True, "data": units}

    @router.get("/shipment/shipment-records/units")
    @router.get("/shipment/shipment-records/units/")
    async def shipment_record_units_compat():
        units = _distinct_customer_purchase_units()
        return {"success": True, "data": units, "units": units}

    @router.get("/customers/{customer_id}", response_model=None)
    async def customers_get(customer_id: int):
        import sqlite3
        db_path = get_database_path()
        if not db_path.exists():
            return JSONResponse({"success": False, "error": "not found"}, status_code=404)
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM customers WHERE id = ?", (customer_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return JSONResponse({"success": False, "error": "not found"}, status_code=404)
        return {"success": True, "data": dict(row)}

    @router.post("/customers", response_model=None)
    async def customers_add(data: dict):
        import sqlite3, datetime
        db_path = get_database_path()
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        now = datetime.datetime.now().isoformat()
        cur.execute(
            "INSERT INTO customers (source_file, customer_name, contact_person, contact_phone, address, purchase_unit, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                data.get("source_file", ""),
                data.get("customer_name", ""),
                data.get("contact_person", ""),
                data.get("contact_phone", ""),
                data.get("address", ""),
                data.get("purchase_unit", ""),
                now, now,
            ),
        )
        new_id = cur.lastrowid
        conn.commit()
        conn.close()
        return {"success": True, "data": {"id": new_id}}

    @router.put("/customers/{customer_id}", response_model=None)
    async def customers_update(customer_id: int, data: dict):
        import sqlite3, datetime
        db_path = get_database_path()
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        now = datetime.datetime.now().isoformat()
        cur.execute(
            "UPDATE customers SET customer_name=?, contact_person=?, contact_phone=?, address=?, purchase_unit=?, updated_at=? WHERE id=?",
            (
                data.get("customer_name", ""),
                data.get("contact_person", ""),
                data.get("contact_phone", ""),
                data.get("address", ""),
                data.get("purchase_unit", ""),
                now,
                customer_id,
            ),
        )
        conn.commit()
        conn.close()
        return {"success": True}

    @router.delete("/customers/{customer_id}", response_model=None)
    async def customers_delete(customer_id: int):
        import sqlite3
        db_path = get_database_path()
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
        conn.commit()
        conn.close()
        return {"success": True}

    @router.post("/customers/batch-delete", response_model=None)
    async def customers_batch_delete(data: dict):
        import sqlite3
        ids = data.get("ids") or []
        if not ids:
            return {"success": True}
        db_path = get_database_path()
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        placeholders = ",".join("?" * len(ids))
        cur.execute(f"DELETE FROM customers WHERE id IN ({placeholders})", ids)
        conn.commit()
        conn.close()
        return {"success": True}

    @router.post("/customers/import", response_model=None)
    async def customers_import(file: UploadFile = File(...)):
        import sqlite3, datetime, tempfile, shutil, openpyxl
        db_path = get_database_path()
        suffix = Path(file.filename or "import.xlsx").suffix.lower()
        if suffix not in {".xlsx", ".xlsm", ".xls"}:
            return JSONResponse({"success": False, "error": "unsupported file type"}, status_code=400)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        try:
            wb = openpyxl.load_workbook(tmp_path, data_only=True)
            ws = wb.active
            headers = [str(c.value or "").strip() for c in ws[1]]
            name_idx = headers.index("客户名称") if "客户名称" in headers else 0
            contact_idx = headers.index("联系人") if "联系人" in headers else -1
            phone_idx = headers.index("电话") if "电话" in headers else -1
            addr_idx = headers.index("地址") if "地址" in headers else -1
            now = datetime.datetime.now().isoformat()
            conn = sqlite3.connect(str(db_path))
            cur = conn.cursor()
            count = 0
            for row in ws.iter_rows(min_row=2, values_only=True):
                name = str(row[name_idx] or "").strip() if name_idx < len(row) else ""
                if not name:
                    continue
                contact = str(row[contact_idx]) if contact_idx >= 0 and contact_idx < len(row) else ""
                phone = str(row[phone_idx]) if phone_idx >= 0 and phone_idx < len(row) else ""
                addr = str(row[addr_idx]) if addr_idx >= 0 and addr_idx < len(row) else ""
                cur.execute(
                    "INSERT INTO customers (source_file, customer_name, contact_person, contact_phone, address, purchase_unit, created_at, updated_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (file.filename or "", name, contact, phone, addr, "", now, now),
                )
                count += 1
            conn.commit()
            conn.close()
            return {"success": True, "imported": count}
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    app.include_router(router, prefix=f"/api/mods/{mod_id}")
    app.include_router(router, prefix=f"/api/mod/{mod_id}")
    logger.info(
        "Mod taiyangniao-pro FastAPI routes: /api/mods/%s/* and /api/mod/%s/*",
        mod_id,
        mod_id,
    )


def mod_init():
    logger.info("Mod taiyangniao-pro initialized")
