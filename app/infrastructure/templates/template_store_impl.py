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

    def _discover_excel_templates(self) -> List[Dict]:
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

        templates: List[Dict] = []
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
                        "FROM templates "
                        "WHERE is_active IS NULL OR is_active = 1"
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

    @staticmethod
    def _build_default_grid_preview(headers: List[str], sample_row: Dict[str, object]) -> Dict:
        header_cells = [
            {"row": 1, "col": index + 1, "text": header, "rowspan": 1, "colspan": 1}
            for index, header in enumerate(headers)
        ]
        value_cells = [
            {
                "row": 2,
                "col": index + 1,
                "text": "" if sample_row.get(header) is None else str(sample_row.get(header)),
                "rowspan": 1,
                "colspan": 1,
            }
            for index, header in enumerate(headers)
        ]
        return {"sheet_name": "默认模板", "rows": [header_cells, value_cells]}

    def _system_default_export_templates(self) -> List[Dict]:
        """系统默认导出模板（无真实文件，反映当前硬编码导出结构）。"""
        orders_headers = ["产品型号", "产品名称", "数量", "单价", "金额"]
        orders_sample = {
            "产品型号": "M001",
            "产品名称": "示例产品",
            "数量": 10,
            "单价": 12.5,
            "金额": 125.0,
        }
        shipment_headers = ["购买单位", "产品名称", "型号", "数量", "单价", "金额", "状态", "创建时间"]
        shipment_sample = {
            "购买单位": "七彩乐园",
            "产品名称": "示例产品",
            "型号": "XH-01",
            "数量": 20,
            "单价": 6.5,
            "金额": 130.0,
            "状态": "已出货",
            "创建时间": "2026-03-25 10:30:00",
        }
        customer_headers = ["ID", "客户名称", "联系人", "电话", "地址"]
        customer_sample = {
            "ID": 1,
            "客户名称": "示例客户",
            "联系人": "张三",
            "电话": "13800000000",
            "地址": "示例地址",
        }
        product_headers = ["产品编码", "产品名称", "规格型号", "价格"]
        product_sample = {
            "产品编码": "P001",
            "产品名称": "示例产品",
            "规格型号": "500ml",
            "价格": 25.0,
        }
        material_headers = ["原材料编码", "名称", "分类", "规格", "单位", "库存数量", "单价", "供应商"]
        material_sample = {
            "原材料编码": "RM001",
            "名称": "示例原料",
            "分类": "基础材料",
            "规格": "25kg/袋",
            "单位": "袋",
            "库存数量": 120,
            "单价": 35.5,
            "供应商": "示例供应商",
        }
        return [
            {
                "id": "system-default:orders",
                "name": "发货单导出默认模板",
                "template_type": "发货单",
                "business_scope": "orders",
                "category": "excel",
                "source": "system-default",
                "exists": False,
                "path": None,
                "file_path": None,
                "preview_capable": True,
                "is_active": 1,
                "fields": [
                    {"label": "产品型号", "value": "", "type": "dynamic"},
                    {"label": "产品名称", "value": "", "type": "dynamic"},
                    {"label": "数量", "value": "", "type": "dynamic"},
                    {"label": "单价", "value": "", "type": "dynamic"},
                    {"label": "金额", "value": "", "type": "dynamic"},
                ],
                "preview_data": {
                    "sample_rows": [orders_sample],
                    "sheet_name": "发货单",
                    "grid_preview": self._build_default_grid_preview(orders_headers, orders_sample),
                },
            },
            {
                "id": "system-default:shipmentRecords",
                "name": "出货记录导出默认模板",
                "template_type": "出货记录",
                "business_scope": "shipmentRecords",
                "category": "excel",
                "source": "system-default",
                "exists": False,
                "path": None,
                "file_path": None,
                "preview_capable": True,
                "is_active": 1,
                "fields": [
                    {"label": "购买单位", "value": "", "type": "dynamic"},
                    {"label": "产品名称", "value": "", "type": "dynamic"},
                    {"label": "型号", "value": "", "type": "dynamic"},
                    {"label": "数量", "value": "", "type": "dynamic"},
                    {"label": "单价", "value": "", "type": "dynamic"},
                    {"label": "金额", "value": "", "type": "dynamic"},
                    {"label": "状态", "value": "", "type": "dynamic"},
                    {"label": "创建时间", "value": "", "type": "dynamic"},
                ],
                "preview_data": {
                    "sample_rows": [shipment_sample],
                    "sheet_name": "出货记录",
                    "grid_preview": self._build_default_grid_preview(shipment_headers, shipment_sample),
                },
            },
            {
                "id": "system-default:customers",
                "name": "客户管理导出默认模板",
                "template_type": "客户",
                "business_scope": "customers",
                "category": "excel",
                "source": "system-default",
                "exists": False,
                "path": None,
                "file_path": None,
                "preview_capable": True,
                "is_active": 1,
                "fields": [
                    {"label": "ID", "value": "", "type": "dynamic"},
                    {"label": "客户名称", "value": "", "type": "dynamic"},
                    {"label": "联系人", "value": "", "type": "dynamic"},
                    {"label": "电话", "value": "", "type": "dynamic"},
                    {"label": "地址", "value": "", "type": "dynamic"},
                ],
                "preview_data": {
                    "sample_rows": [customer_sample],
                    "sheet_name": "客户列表",
                    "grid_preview": self._build_default_grid_preview(customer_headers, customer_sample),
                },
            },
            {
                "id": "system-default:products",
                "name": "产品管理导出默认模板",
                "template_type": "产品",
                "business_scope": "products",
                "category": "excel",
                "source": "system-default",
                "exists": False,
                "path": None,
                "file_path": None,
                "preview_capable": True,
                "is_active": 1,
                "fields": [
                    {"label": "ID", "value": "", "type": "dynamic"},
                    {"label": "产品编码", "value": "", "type": "dynamic"},
                    {"label": "产品名称", "value": "", "type": "dynamic"},
                    {"label": "规格型号", "value": "", "type": "dynamic"},
                    {"label": "价格", "value": "", "type": "dynamic"},
                    {"label": "数量", "value": "", "type": "dynamic"},
                ],
                "preview_data": {
                    "sample_rows": [product_sample],
                    "sheet_name": "产品列表",
                    "grid_preview": self._build_default_grid_preview(product_headers, product_sample),
                },
            },
            {
                "id": "system-default:materials",
                "name": "原材料管理导出默认模板",
                "template_type": "原材料",
                "business_scope": "materials",
                "category": "excel",
                "source": "system-default",
                "exists": False,
                "path": None,
                "file_path": None,
                "preview_capable": True,
                "is_active": 1,
                "fields": [
                    {"label": "原材料编码", "value": "", "type": "dynamic"},
                    {"label": "名称", "value": "", "type": "dynamic"},
                    {"label": "分类", "value": "", "type": "dynamic"},
                    {"label": "规格", "value": "", "type": "dynamic"},
                    {"label": "单位", "value": "", "type": "dynamic"},
                    {"label": "库存数量", "value": "", "type": "dynamic"},
                    {"label": "单价", "value": "", "type": "dynamic"},
                    {"label": "供应商", "value": "", "type": "dynamic"},
                ],
                "preview_data": {
                    "sample_rows": [material_sample],
                    "sheet_name": "原材料列表",
                    "grid_preview": self._build_default_grid_preview(material_headers, material_sample),
                },
            },
        ]

    def list_templates(self) -> List[Dict]:
        # DB 为主，自动发现文件模板为辅，再补 legacy（仅存在的文件）
        templates = self._db_templates()
        templates.extend(self._system_default_export_templates())
        templates.extend(self._discover_excel_templates())
        templates.extend([t for t in self._legacy_templates() if t.get("exists")])

        # 按文件路径去重，避免 legacy 与 fs_scan 重复展示
        deduped: List[Dict] = []
        seen = set()
        for tpl in templates:
            path = str(tpl.get("path") or "").strip()
            key = os.path.normcase(os.path.abspath(path)) if path else str(tpl.get("id") or "")
            if key in seen:
                continue
            seen.add(key)
            deduped.append(tpl)
        return deduped

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

        # 1.5) 支持 "fs:<filename>" 形式（文件扫描来源）
        if template_id.startswith("fs:"):
            filename = template_id.split(":", 1)[1]
            for folder in [self._base_dir, self._template_dir, os.path.join(self._base_dir, "resources", "templates")]:
                path = os.path.join(folder, filename)
                if os.path.exists(path):
                    return path

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

