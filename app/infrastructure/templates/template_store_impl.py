from __future__ import annotations

import os
import shutil
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import text

from app.application.ports.template_store import TemplateStorePort
from app.db.session import get_db


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

    def _legacy_templates(self) -> List[Dict]:
        common = [
            {"id": "shipment", "name": "发货单模板", "filename": "发货单模板.xlsx"},
            {"id": "fallback", "name": "备用模板", "filename": "尹玉华132.xlsx"},
        ]
        out: List[Dict] = []
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

    @staticmethod
    def _map_category(template_type: Optional[str]) -> str:
        t = (template_type or "").strip().lower()
        if any(k in t for k in ["标签", "label", "print", "打印"]):
            return "label_print"
        return "excel"

    def _db_templates(self) -> List[Dict]:
        """从 templates 表读取模板元数据（若表不存在则返回空列表）。"""
        try:
            with get_db() as db:
                # templates(id, template_key, template_name, template_type, original_file_path, is_active, ...)
                rows = db.execute(
                    text(
                        "SELECT id, template_key, template_name, template_type, original_file_path, is_active "
                        "FROM templates"
                    )
                ).fetchall()
        except Exception:
            return []

        out: List[Dict] = []
        for r in rows:
            path = r.original_file_path if getattr(r, "original_file_path", None) else None
            exists = bool(path and os.path.exists(path))
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
                    "category": self._map_category(getattr(r, "template_type", "")),
                    "preview_capable": exists,
                    "is_active": getattr(r, "is_active", 1),
                    "source": "db",
                }
            )
        return out

    def list_templates(self) -> List[Dict]:
        # DB 为主，后面再补 legacy 兼容模板
        templates = self._db_templates()
        templates.extend(self._legacy_templates())
        return templates

    def list_by_type(self, template_type: str, active_only: bool = True) -> List[Dict]:
        db_templates = [
            t for t in self._db_templates() if t.get("template_type") == template_type
        ]
        if active_only:
            db_templates = [t for t in db_templates if t.get("is_active", 1)]
        return db_templates

    def get_default_for_type(self, template_type: str) -> Optional[Dict]:
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

    def resolve_template_file(self, template_id: str) -> Optional[str]:
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

        # 2) 模板文件路由目前仍使用 "shipment"/"fallback" 这种字符串 ID，继续走 legacy 逻辑
        templates = self._legacy_templates()
        t = next((x for x in templates if x["id"] == template_id), None)
        if not t:
            return None
        return t.get("path")

    def save_template_file(self, source_name: str, target_name: str, overwrite: bool) -> Dict:
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

