"""
导出工具应用层函数 — 从 app.infrastructure.documents 组装业务逻辑。

来源：原 app.legacy.price_list_docx_export 与 app.infrastructure.documents.price_list_export。
预计在 Phase 4/5 完整 DDD 重构后，随领域服务落到 app.domain.documents。
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def handle_price_list_export(
    params: dict[str, Any],
    workspace_root: str | None = None,
) -> dict[str, Any]:
    """
    价格表导出工具入口（替换 LOST_LEGACY 中的同名符号）。

    参数:
        params: {
            customer_name: str,      # 必填
            keyword: str | None,     # 产品筛选关键词
            export_date: str | None, # 报价日期
            template_slug: str | None,
        }
        workspace_root: 仓库根路径（用于查找模板）

    返回:
        {success: bool, file_path: str | None, message: str, ...}
    """
    customer_name = str(params.get("customer_name") or "").strip()
    keyword = str(params.get("keyword") or "").strip() or None
    export_date = str(params.get("export_date") or "").strip() or None
    template_slug = str(params.get("template_slug") or "").strip() or None

    if not customer_name:
        return {"success": False, "message": "缺少客户名称，无法生成价格表"}

    # 1. 拉取产品列表
    try:
        from app.application import get_product_app_service

        svc = get_product_app_service()
        products = svc.search_products(keyword=keyword) if keyword else svc.get_all_products()
        if not isinstance(products, list):
            products = []
    except Exception as e:
        logger.error("price_list_export: 获取产品失败: %s", e)
        return {"success": False, "message": f"获取产品列表失败: {e}"}

    # 2. 生成 Word 文件
    try:
        from app.infrastructure.documents.price_list_export import (
            build_price_list_docx_bytes,
            resolve_price_list_docx_template,
        )

        template_path, _ = resolve_price_list_docx_template(slug=template_slug)
        doc_bytes = build_price_list_docx_bytes(
            template_path,
            customer_name=customer_name,
            quote_date=export_date,
            products=products,
        )
    except Exception as e:
        logger.error("price_list_export: 生成 Word 失败: %s", e)
        return {"success": False, "message": f"价格表生成失败: {e}"}

    # 3. 写入临时文件
    try:
        suffix = f"价格表_{customer_name}.docx"
        out_dir = (
            Path(workspace_root) / "shipment_outputs"
            if workspace_root
            else Path(tempfile.gettempdir())
        )
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / suffix
        out_path.write_bytes(doc_bytes)
        return {
            "success": True,
            "file_path": str(out_path),
            "filename": suffix,
            "message": f"价格表已生成：{suffix}",
            "customer_name": customer_name,
            "product_count": len(products),
        }
    except Exception as e:
        logger.error("price_list_export: 写文件失败: %s", e)
        return {"success": False, "message": f"写文件失败: {e}"}
