"""
针对仓库内报价样例 ``424/26年出货单打印/鸿瑞达报价26年.xlsx`` 的解析与导入干跑测试。

版式：前几行为公司抬头；某行 ``客户名称：… 报价日期：…``；下一行为
``编号 / 产品名称 / 规格 / 调价前 / 调价后`` 表头；以下为产品行。
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

QUOTE_PATH = Path(__file__).resolve().parents[2] / "424" / "26年出货单打印" / "鸿瑞达报价26年.xlsx"


def _norm_cell(s: Any) -> str:
    if s is None or (isinstance(s, float) and s != s):
        return ""
    t = str(s).strip().replace(" ", "").replace("\u3000", "")
    return t


def parse_quote_sheet(df: pd.DataFrame) -> tuple[str, str, list[dict[str, Any]]]:
    """
    从 ``header=None`` 读入的 DataFrame 解析客户名、报价日期、产品 items（供 ``products_bulk_import``）。
    """
    customer = ""
    quote_date = ""
    header_idx: int | None = None
    for i in range(min(20, len(df))):
        cell0 = df.iloc[i, 0] if df.shape[1] > 0 else ""
        s0 = str(cell0) if cell0 is not None and not (isinstance(cell0, float) and cell0 != cell0) else ""
        if "客户名称" in s0:
            compact = s0.replace(" ", "").replace("\u3000", "")
            m = re.search(r"客户名称[：:](.+?)报价日期[：:]", compact)
            if m:
                customer = m.group(1).strip()
            m2 = re.search(r"报价日期[：:](.+)$", compact)
            if m2:
                quote_date = m2.group(1).strip()
        joined = "".join(_norm_cell(x) for x in df.iloc[i])
        if "产品名称" in joined and ("编号" in joined or "编" in joined):
            header_idx = i
            break
    if not customer or header_idx is None:
        raise ValueError(f"无法解析客户或表头: customer={customer!r}, header_idx={header_idx}")
    hdr = df.iloc[header_idx]
    idx_name = idx_model = idx_spec = idx_price = None
    for j in range(df.shape[1]):
        h = _norm_cell(hdr.iloc[j])
        if not h:
            continue
        if "产品名称" in h:
            idx_name = j
        if "编号" in h or h == "编号":
            idx_model = j
        if "规格" in h:
            idx_spec = j
        if "调价后" in h:
            idx_price = j
    if idx_name is None or idx_price is None:
        raise ValueError(f"无法定位列: name={idx_name}, price={idx_price}")
    if idx_model is None:
        idx_model = 0
    if idx_spec is None:
        idx_spec = min(idx_name + 1, df.shape[1] - 1)

    items: list[dict[str, Any]] = []
    for r in range(header_idx + 1, len(df)):
        name = str(df.iloc[r, idx_name]).strip() if pd.notna(df.iloc[r, idx_name]) else ""
        if not name or name.lower() == "nan":
            continue
        model = str(df.iloc[r, idx_model]).strip() if pd.notna(df.iloc[r, idx_model]) else ""
        spec = str(df.iloc[r, idx_spec]).strip() if pd.notna(df.iloc[r, idx_spec]) else ""
        price_cell = df.iloc[r, idx_price]
        items.append(
            {
                "model_number": model,
                "name": name,
                "specification": spec,
                "price": price_cell,
            }
        )
    return customer, quote_date, items


@pytest.fixture(scope="module")
def quote_path():
    if not QUOTE_PATH.is_file():
        pytest.skip(f"缺少样例文件: {QUOTE_PATH}")
    return QUOTE_PATH


def test_parse_hongrunda_quote_xlsx(quote_path):
    df = pd.read_excel(quote_path, sheet_name=0, header=None)
    customer, quote_date, items = parse_quote_sheet(df)
    assert "鸿瑞达" in customer
    assert "2026" in quote_date or "4" in quote_date
    assert len(items) >= 15
    first = items[0]
    assert first.get("name")
    assert first.get("model_number") or first.get("name")


def test_hongrunda_quote_bulk_import_payload_shape(quote_path):
    """不连库：确认解析结果可直接作为 ``products_bulk_import`` 的 body。"""
    df = pd.read_excel(quote_path, sheet_name=0, header=None)
    customer, quote_date, items = parse_quote_sheet(df)
    body = {
        "customer_name": customer,
        "quote_date": quote_date,
        "items": items,
        "dry_run": True,
    }
    assert body["customer_name"]
    assert isinstance(body["items"], list)
    for it in body["items"][:3]:
        assert isinstance(it, dict)
        assert it.get("name")
        assert "price" in it
