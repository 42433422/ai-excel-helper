from __future__ import annotations

from typing import Any, Dict, List, Optional


def _normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalize_model_token(value: Any) -> str:
    return _normalize_text(value).replace(" ", "").replace("-", "")


def _to_float_or_none(value: Any) -> Optional[float]:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except Exception:
        return None


def match_product(
    name: str,
    model_number: str,
    tin_spec: Any,
    db_products: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    产品匹配规则（纯领域逻辑，无 DB / 无 I/O）。

    匹配顺序：
    1) 型号精确（忽略空格/中划线）
    2) 同型号多记录时，按规格消歧
    3) 无型号时按名称精确
    4) 兜底名称包含
    """
    if not name and not model_number:
        return None

    name_norm = _normalize_text(name)
    model_norm = _normalize_model_token(model_number)
    spec_norm = _to_float_or_none(tin_spec)

    # 1) 型号精确（严格）
    if model_norm:
        model_exact_matches: List[Dict[str, Any]] = []
        for p in db_products:
            if _normalize_model_token(p.get("model_number")) == model_norm:
                model_exact_matches.append(p)
        if len(model_exact_matches) == 1:
            return model_exact_matches[0]
        if len(model_exact_matches) > 1:
            # 2) 同型号多规格时按规格消歧
            if spec_norm is not None:
                for p in model_exact_matches:
                    p_spec = _to_float_or_none(p.get("specification"))
                    if p_spec is not None and p_spec == spec_norm:
                        return p
            # 严格模式：无法消歧时保持可预期，返回首个型号命中
            return model_exact_matches[0]

    # 3) 无型号时按名称精确
    if name_norm:
        for p in db_products:
            if _normalize_text(p.get("name")) == name_norm:
                return p

    # 4) 名称包含
    if name_norm:
        for p in db_products:
            p_name = _normalize_text(p.get("name"))
            if p_name and (name_norm in p_name or p_name in name_norm):
                return p

    return None


def prepare_parsed_products(
    *,
    input_products: List[Dict[str, Any]],
    db_products: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    将外部输入产品列表转换为 legacy 文档生成器期望的 parsed_products 结构。

    领域职责：
    - 规格/数量/金额推导（quantity_kg, amount）
    - 基于主库产品候选进行匹配（name/model_number 与单价补全）
    - 无法确定产品名称时的跳过规则
    """
    parsed_products: List[Dict[str, Any]] = []

    for p in input_products or []:
        name = p.get("name") or p.get("product_name", "")
        model_number = p.get("model_number", "") or p.get("型号", "")

        quantity_tins = p.get("quantity_tins")
        if quantity_tins is None:
            quantity_tins = p.get("quantity", 0)

        tin_spec = p.get("tin_spec") or p.get("spec") or 10.0

        matched = match_product(str(name or ""), str(model_number or ""), tin_spec, db_products)
        if matched:
            name = matched.get("name") or name
            model_number = matched.get("model_number") or model_number

        # 不再静默丢行：至少保留可识别型号，避免“槽位正确但整行消失”
        if not name:
            name = str(model_number or "").strip()
        if not name:
            continue

        unit_price = p.get("unit_price")
        if unit_price is None:
            unit_price = matched.get("price") if matched else p.get("price", 0)

        quantity_kg = p.get("quantity_kg")
        if quantity_kg is None:
            try:
                quantity_kg = float(quantity_tins or 0) * float(tin_spec or 0)
            except Exception:
                quantity_kg = 0

        amount = p.get("amount")
        if amount is None:
            try:
                amount = float(unit_price or 0) * float(quantity_kg or 0)
            except Exception:
                amount = 0

        parsed_products.append(
            {
                "model_number": model_number,
                "name": name,
                "quantity_kg": quantity_kg,
                "quantity_tins": int(quantity_tins or 0),
                "tin_spec": float(tin_spec or 10.0),
                "unit_price": float(unit_price or 0),
                "amount": float(amount or 0),
            }
        )

    return parsed_products

