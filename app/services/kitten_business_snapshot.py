# -*- coding: utf-8 -*-
"""
小猫分析 · 业务库快照：从原材料、产品、出货表聚合摘要，供 LLM 做成本/库存/趋势类分析（非会计准则报表）。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _fmt_dt(val: Any) -> str:
    if val is None:
        return ""
    if hasattr(val, "isoformat"):
        try:
            return str(val.isoformat())
        except Exception:
            return str(val)
    return str(val)


def build_kitten_business_snapshot(
    *,
    max_material_lines: int = 60,
    max_product_lines: int = 50,
    max_shipment_lines: int = 100,
    max_text_chars: int = 14000,
) -> Dict[str, Any]:
    stats: Dict[str, Any] = {}
    lines: List[str] = [
        "说明：以下为当前业务数据库中的库存与出货快照，可用于原材料成本、库存结构、近期销售等经营分析；",
        "不是会计准则下的财务报表，金额以系统内「单价×数量」估算，分析时请提醒用户以正式账目为准。",
        "",
    ]

    # —— 原材料：全库聚合 + 明细样例 ——
    try:
        from sqlalchemy import Float as SAFloat
        from sqlalchemy import cast, func

        from app.application import get_material_application_service
        from app.db.models.material import Material
        from app.db.session import get_db

        with get_db() as db:
            total_m = (
                db.query(func.count(Material.id))
                .filter(Material.is_active == 1)
                .scalar()
                or 0
            )
            inv_val = db.query(
                func.coalesce(
                    func.sum(
                        cast(Material.quantity, SAFloat)
                        * cast(Material.unit_price, SAFloat)
                    ),
                    0.0,
                )
            ).filter(Material.is_active == 1).scalar()
            inv_val = float(inv_val or 0)
            low_cnt = (
                db.query(func.count(Material.id))
                .filter(
                    Material.is_active == 1,
                    Material.min_stock > 0,
                    Material.quantity < Material.min_stock,
                )
                .scalar()
                or 0
            )

        stats["materials_total"] = int(total_m)
        stats["material_inventory_value_estimate"] = round(inv_val, 2)
        stats["materials_low_stock_count"] = int(low_cnt)

        mat_svc = get_material_application_service()
        page = mat_svc.get_all_materials(page=1, per_page=max_material_lines)
        rows = page.get("data") or []
        stats["materials_sample_lines"] = len(rows)

        lines.append("【原材料】")
        lines.append(
            f"- 在库条目数：{total_m}；按单价×数量估算库存总值：¥{inv_val:.2f}"
        )
        lines.append(
            f"- 低于安全库存条目数（min_stock>0 且 quantity<min_stock）：{low_cnt}"
        )
        lines.append("- 明细样例（按创建时间倒序，最多列示若干条）：")
        for r in rows[:max_material_lines]:
            name = str(r.get("name") or "")
            cat = str(r.get("category") or "")
            qty = r.get("quantity")
            up = r.get("unit_price")
            u = str(r.get("unit") or "")
            sup = str(r.get("supplier") or "")
            suf = f" | 供应商:{sup}" if sup else ""
            lines.append(f"  · {name} | 类:{cat} | 存量:{qty}{u} | 单价:{up}{suf}")
        lines.append("")
    except Exception as e:
        logger.exception("kitten snapshot materials failed: %s", e)
        lines.append("【原材料】读取失败，可提示用户检查原材料模块或数据库。")
        stats["materials_error"] = str(e)

    # —— 产品库：全库聚合 + 明细样例 ——
    try:
        from sqlalchemy import Float as SAFloat
        from sqlalchemy import cast, func

        from app.bootstrap import get_products_service
        from app.db.models.product import Product as ProductModel
        from app.db.session import get_db

        with get_db() as db:
            total_p = (
                db.query(func.count(ProductModel.id))
                .filter(ProductModel.is_active == 1)
                .scalar()
                or 0
            )
            inv_pv = db.query(
                func.coalesce(
                    func.sum(
                        cast(ProductModel.quantity, SAFloat)
                        * cast(ProductModel.price, SAFloat)
                    ),
                    0.0,
                )
            ).filter(ProductModel.is_active == 1).scalar()
            inv_pv = float(inv_pv or 0)

        stats["products_total"] = int(total_p)
        stats["product_inventory_value_estimate"] = round(inv_pv, 2)

        pr = get_products_service().get_products(page=1, per_page=max_product_lines)
        prows = pr.get("data") or []
        stats["products_sample_lines"] = len(prows)

        lines.append("【成品/产品库】")
        lines.append(
            f"- 在架条目数：{total_p}；按单价×数量估算库存货值：¥{inv_pv:.2f}"
        )
        lines.append("- 明细样例：")
        for r in prows[:max_product_lines]:
            lines.append(
                "  · "
                f"{r.get('name')} | 型号:{r.get('model_number')} | 类:{r.get('category')} "
                f"| 单位:{r.get('unit')} | 存量:{r.get('quantity')} | 单价:{r.get('price')}"
            )
        lines.append("")
    except Exception as e:
        logger.exception("kitten snapshot products failed: %s", e)
        lines.append("【成品/产品库】读取失败。")
        stats["products_error"] = str(e)

    # —— 出货：最近若干条（非全历史） ——
    try:
        from app.bootstrap import get_shipment_app_service

        recs = get_shipment_app_service().get_shipment_records(unit_name=None)
        if len(recs) > max_shipment_lines:
            recs = recs[:max_shipment_lines]
        stats["shipments_sample_count"] = len(recs)
        amt = sum(float(x.get("amount") or 0) for x in recs)
        stats["shipments_sample_amount_sum"] = round(amt, 2)

        lines.append("【出货记录】（时间倒序的最近一批，用于观察近期销售结构；合计仅为本批金额之和，非全历史）")
        lines.append(
            f"- 本批条数：{len(recs)}；本批各行 amount 合计：¥{amt:.2f}"
        )
        show = min(45, len(recs))
        for x in recs[:show]:
            lines.append(
                "  · "
                f"{x.get('purchase_unit')} | {x.get('product_name')} | "
                f"kg:{x.get('quantity_kg')} | 听:{x.get('quantity_tins')} | "
                f"¥{x.get('amount')} | {_fmt_dt(x.get('created_at'))}"
            )
        if len(recs) > show:
            lines.append(f"  … 另有 {len(recs) - show} 条未列出")
        lines.append("")
    except Exception as e:
        logger.exception("kitten snapshot shipments failed: %s", e)
        lines.append("【出货记录】读取失败。")
        stats["shipments_error"] = str(e)

    text = "\n".join(lines)
    if len(text) > max_text_chars:
        text = text[: max_text_chars - 24] + "\n…（业务快照已截断）"

    return {
        "success": True,
        "generated_at": _iso_now(),
        "stats": stats,
        "text": text,
    }
