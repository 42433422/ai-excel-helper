from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime
from typing import Any

from sqlalchemy import text

from app.application.ports.template_store import TemplateStorePort
from app.db.session import get_db

logger = logging.getLogger(__name__)


class FileSystemTemplateStore(TemplateStorePort):
    """
    模板库实现：
    - **主来源**: templates 表（表驱动，带 original_file_path / is_active 等）
    - **兼容来源**: 固定文件名（发货单模板.xlsx / 尹玉华132.xlsx），用于老模板与测试
    """

    def __init__(self, base_dir: str):
        self._base_dir = base_dir
        self._template_dir = os.path.join(base_dir, "templates")
        os.makedirs(self._template_dir, exist_ok=True)

    def _legacy_templates(self) -> list[dict]:
        common = [
            {"id": "shipment", "name": "发货单模板", "filename": "发货单模板.xlsx"},
            {"id": "fallback", "name": "备用模板", "filename": "尹玉华132.xlsx"},
        ]
        out: list[dict] = []
        for t in common:
            path1 = os.path.join(self._base_dir, t["filename"])
            path2 = os.path.join(self._template_dir, t["filename"])
            path = path1 if os.path.exists(path1) else (path2 if os.path.exists(path2) else None)
            out.append(
                {
                    "id": t["id"],
                    "name": t["name"],
                    "filename": t["filename"],
                    "exists": bool(path),
                    "path": path,
                    "file_path": path,
                    "template_type": "发货单",
                    "category": "excel",
                    "preview_capable": bool(path),
                    "is_active": 1,
                    "source": "legacy_fs",
                }
            )
        return out

    def _infer_template_type_from_filename(self, filename: str) -> str:
        name = (filename or "").lower()
        if "客户" in name:
            return "客户"
        if "原材料" in name or "材料" in name:
            return "原材料"
        if "产品" in name:
            return "产品"
        if "出货记录" in name:
            return "出货记录"
        if "发货" in name or "出货单" in name:
            return "发货单"
        return "Excel"

    def _discover_excel_templates(self) -> list[dict]:
        """
        从固定目录自动发现 Excel 模板文件：
        - 项目根目录
        - templates 目录
        - resources/templates 目录
        """
        candidates = [
            self._base_dir,
            self._template_dir,
            os.path.join(self._base_dir, "resources", "templates"),
        ]

        templates: list[dict] = []
        seen_paths = set()
        for folder in candidates:
            if not os.path.isdir(folder):
                continue
            try:
                for entry in os.listdir(folder):
                    lower = entry.lower()
                    if lower.startswith("~$"):
                        continue
                    if not (lower.endswith(".xlsx") or lower.endswith(".xls")):
                        continue

                    file_path = os.path.join(folder, entry)
                    if not os.path.isfile(file_path):
                        continue

                    norm_path = os.path.normcase(os.path.abspath(file_path))
                    if norm_path in seen_paths:
                        continue
                    seen_paths.add(norm_path)

                    template_type = self._infer_template_type_from_filename(entry)
                    templates.append(
                        {
                            "id": f"fs:{entry}",
                            "name": os.path.splitext(entry)[0],
                            "filename": entry,
                            "exists": True,
                            "path": file_path,
                            "file_path": file_path,
                            "template_type": template_type,
                            "category": self._map_category(template_type),
                            "preview_capable": True,
                            "is_active": 1,
                            "source": "fs_scan",
                        }
                    )
            except Exception:
                continue
        return templates

    def _discover_word_templates(self) -> list[dict]:
        """从与 Excel 相同的目录自动发现 Word 模板（.docx）。"""
        candidates = [
            self._base_dir,
            self._template_dir,
            os.path.join(self._base_dir, "resources", "templates"),
            os.path.join(self._base_dir, "424", "document_templates"),
        ]
        templates: list[dict] = []
        seen_paths = set()
        for folder in candidates:
            if not os.path.isdir(folder):
                continue
            try:
                for entry in os.listdir(folder):
                    lower = entry.lower()
                    if lower.startswith("~$"):
                        continue
                    if not lower.endswith(".docx"):
                        continue
                    file_path = os.path.join(folder, entry)
                    if not os.path.isfile(file_path):
                        continue
                    norm_path = os.path.normcase(os.path.abspath(file_path))
                    if norm_path in seen_paths:
                        continue
                    seen_paths.add(norm_path)
                    base_name = os.path.splitext(entry)[0]
                    if lower == "price_list_default.docx":
                        base_name = "产品价格表（Word 价目）"
                    templates.append(
                        {
                            "id": f"fs:{entry}",
                            "name": base_name,
                            "filename": entry,
                            "exists": True,
                            "path": file_path,
                            "file_path": file_path,
                            "template_type": "Word",
                            "category": "word",
                            "preview_capable": True,
                            "is_active": 1,
                            "source": "fs_scan",
                        }
                    )
            except Exception:
                continue
        return templates

    @staticmethod
    def _map_category(template_type: str | None) -> str:
        t = (template_type or "").strip().lower()
        if any(k in t for k in ["标签", "label", "print", "打印"]):
            return "label_print"
        return "excel"

    def _db_templates(self) -> list[dict]:
        """从 templates 表读取模板元数据（若表不存在则返回空列表）。"""
        try:
            with get_db() as db:
                # templates(id, template_key, template_name, template_type, original_file_path, is_active, ...)
                rows = db.execute(
                    text(
                        "SELECT id, template_key, template_name, template_type, original_file_path, is_active "
                        "FROM templates "
                        "WHERE is_active IS NULL OR is_active = 1"
                    )
                ).fetchall()
        except Exception:
            return []

        out: list[dict] = []
        for r in rows:
            path = r.original_file_path if getattr(r, "original_file_path", None) else None
            exists = bool(path and os.path.exists(path))
            lower_fp = str(path or "").lower()
            category = (
                "word"
                if lower_fp.endswith((".docx", ".doc"))
                else self._map_category(getattr(r, "template_type", ""))
            )
            out.append(
                {
                    "id": f"db:{r.id}",
                    "db_id": r.id,
                    "template_key": getattr(r, "template_key", None),
                    "name": getattr(r, "template_name", ""),
                    "template_type": getattr(r, "template_type", ""),
                    "filename": os.path.basename(path) if path else None,
                    "exists": exists,
                    "path": path,
                    "file_path": path,
                    "category": category,
                    "preview_capable": exists,
                    "is_active": getattr(r, "is_active", 1),
                    "source": "db",
                }
            )
        return out

    def list_templates(self) -> list[dict]:
        # DB 为主，自动发现文件模板为辅，再补 legacy（仅存在的文件）。
        # 注意：历史上这里还会拼接 `_system_default_export_templates()` 产生的
        # "导出默认模板" 占位条目，但它们带的都是假样例数据（M001/示例产品等），
        # 在前端模板预览页看起来像占位；按产品要求已移除——无真实模板时由前端
        # 的 "虚拟占位/快速创建" 流程兜底，而不再由后端塞入硬编码假数据。
        templates = self._db_templates()
        templates.extend(self._discover_excel_templates())
        templates.extend(self._discover_word_templates())
        templates.extend([t for t in self._legacy_templates() if t.get("exists")])

        # 按文件路径去重，避免 legacy 与 fs_scan 重复展示
        deduped: list[dict] = []
        seen = set()
        for tpl in templates:
            path = str(tpl.get("path") or "").strip()
            key = os.path.normcase(os.path.abspath(path)) if path else str(tpl.get("id") or "")
            if key in seen:
                continue
            seen.add(key)
            deduped.append(tpl)
        return deduped

    def list_by_type(self, template_type: str, active_only: bool = True) -> list[dict]:
        db_templates = [t for t in self._db_templates() if t.get("template_type") == template_type]
        if active_only:
            db_templates = [t for t in db_templates if t.get("is_active", 1)]
        return db_templates

    def get_default_for_type(self, template_type: str) -> dict | None:
        # 1) 优先从 DB 中选出 active 且文件存在的模板，按 db_id 倒排取一个
        candidates = [
            t
            for t in self._db_templates()
            if t.get("template_type") == template_type
            and t.get("is_active", 1)
            and t.get("path")
            and os.path.exists(t["path"])
        ]
        if candidates:
            candidates.sort(key=lambda x: x.get("db_id", 0), reverse=True)
            return candidates[0]

        # 2) DB 没有可用模板时，回退到 legacy 发货单模板
        if template_type == "发货单":
            for t in self._legacy_templates():
                if t["id"] == "shipment" and t.get("path"):
                    return t

        return None

    def resolve_template_file(self, template_id: str) -> str | None:
        # 1) 支持 "db:<id>" 形式（表驱动）
        if template_id.startswith("db:"):
            try:
                db_id = int(template_id.split(":", 1)[1])
            except ValueError:
                db_id = None
            if db_id is not None:
                try:
                    with get_db() as db:
                        row = db.execute(
                            text(
                                "SELECT original_file_path FROM templates "
                                "WHERE id = :id AND (is_active IS NULL OR is_active = 1)"
                            ),
                            {"id": db_id},
                        ).fetchone()
                    if row and row.original_file_path and os.path.exists(row.original_file_path):
                        return row.original_file_path
                except Exception:
                    pass

        # 1.5) 支持 "fs:<filename>" 形式（文件扫描来源）
        if template_id.startswith("fs:"):
            filename = template_id.split(":", 1)[1]
            for folder in [
                self._base_dir,
                self._template_dir,
                os.path.join(self._base_dir, "resources", "templates"),
                os.path.join(self._base_dir, "424", "document_templates"),
            ]:
                path = os.path.join(folder, filename)
                if os.path.exists(path):
                    return path

        # 2) 模板文件路由目前仍使用 "shipment"/"fallback" 这种字符串 ID，继续走 legacy 逻辑
        templates = self._legacy_templates()
        t = next((x for x in templates if x["id"] == template_id), None)
        if not t:
            return None
        return t.get("path")

    def save_template_file(self, source_name: str, target_name: str, overwrite: bool) -> dict:
        source_name = (source_name or "").strip() or "尹玉华132.xlsx"
        target_name = (target_name or "").strip() or "发货单模板.xlsx"

        source_path = os.path.join(self._base_dir, source_name)
        if not os.path.exists(source_path):
            alt = os.path.join(self._template_dir, source_name)
            source_path = alt if os.path.exists(alt) else source_path

        target_path = os.path.join(self._base_dir, target_name)

        if not os.path.exists(source_path):
            return {"success": False, "message": f"源模板不存在: {source_name}"}

        if os.path.exists(target_path) and not overwrite:
            return {
                "success": True,
                "message": "目标模板已存在，未覆盖",
                "saved": False,
                "template_name": target_name,
                "template_path": target_path,
            }

        # 复制文件（注意：测试中会对 shutil.copy2 与 os.path.exists 做 Mock，这里保持不变即可）
        shutil.copy2(source_path, target_path)

        # 记录 / 更新 templates 表（表驱动）——失败不影响返回
        try:
            from sqlalchemy import text as sql_text

            with get_db() as db:
                # 这里不强制唯一约束，只是简单插入一条记录，并将同类型旧记录标记为非激活
                db.execute(
                    sql_text(
                        """
                        UPDATE templates
                        SET is_active = 0, updated_at = :updated_at
                        WHERE template_type = :template_type
                        """
                    ),
                    {"template_type": "发货单", "updated_at": datetime.now()},
                )
                db.execute(
                    sql_text(
                        """
                        INSERT INTO templates (
                            template_key, template_name, template_type,
                            original_file_path, analyzed_data, editable_config,
                            zone_config, merged_cells_config, style_config,
                            business_rules, is_active
                        ) VALUES (
                            :template_key, :template_name, :template_type,
                            :original_file_path, :analyzed_data, :editable_config,
                            :zone_config, :merged_cells_config, :style_config,
                            :business_rules, :is_active
                        )
                        """
                    ),
                    {
                        "template_key": f"FS_{target_name}",
                        "template_name": "发货单模板",
                        "template_type": "发货单",
                        "original_file_path": target_path,
                        "analyzed_data": "{}",
                        "editable_config": "{}",
                        "zone_config": "{}",
                        "merged_cells_config": "{}",
                        "style_config": "{}",
                        "business_rules": "{}",
                        "is_active": 1,
                    },
                )
                db.commit()
        except Exception:
            # 表不存在或结构不兼容时忽略，仍保持文件模式可用
            pass

        return {
            "success": True,
            "message": "模板保存成功",
            "saved": True,
            "template_name": target_name,
            "template_path": target_path,
        }

    def save_template(self, template_data: dict[str, Any]) -> dict[str, Any]:
        """将模板元数据写入 templates 表（供 POST /api/excel/templates 等使用）。"""
        name = (template_data.get("template_name") or "").strip()
        if not name:
            return {"success": False, "message": "模板名称不能为空"}

        def _dumps(obj: Any) -> str | None:
            if obj is None:
                return None
            return json.dumps(obj, ensure_ascii=False)

        template_type = template_data.get("template_type") or "Excel"
        template_key = (template_data.get("template_key") or f"tpl_{name}").strip()
        original_file_path = template_data.get("original_file_path") or ""

        try:
            with get_db() as db:
                res = db.execute(
                    text(
                        """
                        INSERT INTO templates (
                            template_key, template_name, template_type, original_file_path,
                            analyzed_data, editable_config, zone_config, merged_cells_config,
                            style_config, business_rules, is_active, created_at, updated_at
                        ) VALUES (
                            :template_key, :template_name, :template_type, :original_file_path,
                            :analyzed_data, :editable_config, :zone_config, :merged_cells_config,
                            :style_config, :business_rules, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                        )
                        """
                    ),
                    {
                        "template_key": template_key,
                        "template_name": name,
                        "template_type": template_type,
                        "original_file_path": original_file_path or None,
                        "analyzed_data": _dumps(template_data.get("analyzed_data")),
                        "editable_config": _dumps(template_data.get("editable_config")),
                        "zone_config": _dumps(template_data.get("zone_config")),
                        "merged_cells_config": _dumps(template_data.get("merged_cells_config")),
                        "style_config": _dumps(template_data.get("style_config")),
                        "business_rules": _dumps(template_data.get("business_rules")),
                    },
                )
                db.commit()
                new_id = getattr(res, "lastrowid", None)
            return {"success": True, "message": "模板创建成功", "id": new_id}
        except Exception as e:
            logger.error("save_template failed: %s", e, exc_info=True)
            return {"success": False, "message": str(e)}
