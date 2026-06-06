"""
库存/采购/报表路由 — 已迁移存根

原端点已按业务域拆分到独立模块：
- /api/inventory/*  → app/fastapi_routes/inventory.py  (tag: inventory)
- /api/purchase/*   → app/fastapi_routes/purchase.py   (tag: purchase)
- /api/report/*     → app/fastapi_routes/reports.py    (tag: reports)

本文件保留空 router 供 legacy_gaps_batch1.py 聚合 include 使用，
等待 Phase 4B 将 legacy_gaps_batch1 拆解后可删除本文件。
"""

from fastapi import APIRouter

router = APIRouter(tags=["legacy-inventory"], deprecated=True)
