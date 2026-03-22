# -*- coding: utf-8 -*-
"""
文件分析应用服务

提供统一文件分析能力：
- 文件类型识别（扩展名 + SQLite 文件头）
- SQLite .db 数据库分析
- 返回分析结果和建议用途
"""

import logging
import os
import sqlite3
import uuid
from typing import Any, Dict, Optional, Tuple

from werkzeug.utils import secure_filename

from app.utils.path_utils import get_upload_dir

logger = logging.getLogger(__name__)


class FileAnalysisService:
    """
    文件分析服务类

    负责分析上传文件，识别类型并提取元数据。
    """

    def __init__(self):
        self.upload_dir = get_upload_dir()

    def analyze_file(
        self,
        upload_file,
        purpose: str = "general"
    ) -> Dict[str, Any]:
        """
        分析上传文件

        Args:
            upload_file: 上传的文件对象
            purpose: 预期用途提示

        Returns:
            分析结果字典
        """
        if not upload_file or not upload_file.filename:
            return {"success": False, "message": "未选择文件"}

        raw_filename = upload_file.filename
        ext = self._get_extension(raw_filename, upload_file.filename)
        filename = secure_filename(raw_filename)

        saved_name = f"{uuid.uuid4().hex}_{filename}"
        saved_path = os.path.join(self.upload_dir, saved_name)
        upload_file.save(saved_path)

        ext = self._detect_sqlite_by_header(saved_path, ext)

        if ext == ".db":
            return self._analyze_sqlite_db(saved_path, saved_name, raw_filename, filename)

        return {
            "success": False,
            "message": f"暂不支持通过本接口解析 {ext}；当前版本仅对 .db（SQLite）内置读取能力。",
            "parser_used": "unsupported",
            "extension": ext
        }

    def _get_extension(self, raw_filename: str, fallback_filename: str) -> str:
        """获取文件扩展名"""
        ext = os.path.splitext(raw_filename)[1].lower()
        if not ext and raw_filename.lower().endswith(".db"):
            ext = ".db"
        if not ext:
            filename = secure_filename(fallback_filename)
            ext = os.path.splitext(filename)[1].lower()
            if not ext and filename.lower().endswith(".db"):
                ext = ".db"
        return ext

    def _detect_sqlite_by_header(self, file_path: str, ext: str) -> str:
        """通过文件头检测是否为 SQLite 数据库"""
        try:
            with open(file_path, "rb") as f:
                header = f.read(16)
            if header.startswith(b"SQLite format 3"):
                return ".db"
        except Exception:
            pass
        return ext

    def _analyze_sqlite_db(
        self,
        saved_path: str,
        saved_name: str,
        raw_filename: str,
        filename: str
    ) -> Dict[str, Any]:
        """分析 SQLite 数据库文件"""
        conn = None
        try:
            conn = sqlite3.connect(saved_path)
            cur = conn.cursor()

            tables = cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            table_names = [t[0] for t in tables if t and t[0]]

            focus_tables = table_names[:10]
            table_columns = {}
            for t in focus_tables:
                try:
                    cols = cur.execute(f"PRAGMA table_info('{t}')").fetchall()
                    table_columns[t] = [c[1] for c in cols if c and len(c) >= 2]
                except Exception:
                    table_columns[t] = []

            suggested_use = self._determine_suggested_use(table_names, table_columns)
            main_tables = focus_tables[:6] if focus_tables else []
            main_tables_text = "、".join(main_tables) if main_tables else "-"

            unit_name_guess = self._extract_unit_name_guess(raw_filename, filename)

            unit_candidates = []
            if suggested_use == "unit_products_db":
                unit_candidates = self._extract_unit_candidates(cur, table_names)

            ai_summary = (
                f"已识别 SQLite 数据库（.db）。库内表数：{len(table_names)}；"
                f"主要表：{main_tables_text}。\n"
                f"建议下一步用途：{suggested_use}。"
            )

            return {
                "success": True,
                "parser_used": "sqlite_db",
                "extension": ".db",
                "text_preview": "",
                "ai_summary": ai_summary,
                "analyzed": True,
                "suggested_use": suggested_use,
                "saved_name": saved_name,
                "unit_name_guess": unit_name_guess,
                "unit_candidates": unit_candidates,
                "db_meta": {
                    "table_count": len(table_names),
                    "tables": focus_tables,
                    "table_columns": table_columns
                }
            }
        except Exception as e:
            logger.exception(f"SQLite 数据库分析失败：{e}")
            return {
                "success": False,
                "message": f"文件分析失败：{str(e)}"
            }
        finally:
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass

    def _determine_suggested_use(
        self,
        table_names: list,
        table_columns: Dict[str, list]
    ) -> str:
        """根据表结构确定建议用途"""
        lower_tables = {x.lower() for x in table_names}

        if "msg" in lower_tables or "contact" in lower_tables:
            return "wechat_db_search"
        if "purchase_units" in lower_tables:
            return "purchase_units_db"
        if "customers" in lower_tables:
            return "customers_db"

        products_table = next(
            (t for t in table_names if t and t.lower() == "products"),
            None
        )
        if products_table:
            products_cols_lower = [c.lower() for c in (table_columns.get(products_table) or [])]
            has_required_cols = (
                "model_number" in products_cols_lower
                and "name" in products_cols_lower
            )
            has_unit_col = "unit" in products_cols_lower
            is_unit_products_lib = (
                products_table is not None
                and has_required_cols
                and (
                    len(table_names) <= 2
                    or (
                        "customers" not in lower_tables
                        and "purchase_units" not in lower_tables
                    )
                )
                and has_unit_col
            )
            if is_unit_products_lib:
                return "unit_products_db"

        return "sqlite_db"

    def _extract_unit_name_guess(self, raw_filename: str, filename: str) -> str:
        """从文件名提取购买单位名称猜测"""
        try:
            base = os.path.splitext(raw_filename or "")[0] or os.path.splitext(filename or "")[0]
            return (base or "").strip()
        except Exception:
            return ""

    def _extract_unit_candidates(
        self,
        cur: sqlite3.Cursor,
        table_names: list
    ) -> list:
        """从 unit_products_db 提取购买单位候选列表"""
        products_table = next(
            (t for t in table_names if t and t.lower() == "products"),
            None
        )
        if not products_table:
            return []

        try:
            candidates = [
                r[0] for r in cur.execute(
                    f'SELECT DISTINCT unit FROM "{products_table}" '
                    f'WHERE unit IS NOT NULL AND TRIM(unit) != "" '
                    f"LIMIT 10"
                ).fetchall()
                if r and r[0]
            ]
            return candidates
        except Exception:
            return []


_file_analysis_app_service_instance = None


def get_file_analysis_app_service() -> FileAnalysisService:
    """获取文件分析服务单例"""
    global _file_analysis_app_service_instance
    if _file_analysis_app_service_instance is None:
        _file_analysis_app_service_instance = FileAnalysisService()
    return _file_analysis_app_service_instance
