"""
销售合同生成（与 ``/api/sales-contract/generate`` 及 Planner 工具同源）：

**仅**通过 ``fill_sales_contract_excel_template`` 写 Excel：源文件须为 ``.xls/.xlsx/.xlsm``
（``424/document_templates/送货单.xls`` 版式），产物为 ``.xlsx``。

``document_templates.role=sales_contract_docx`` 下可登记 Word（``.docx``）供预览与下拉展示；
若用户选中 Word 模板发起生成，则自动改用语义固定的 **送货单 Excel**（见
``resolve_sales_delivery_excel_template_with_meta``），不再尝试用 Word 填表。
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def _parse_quantity(value: str) -> int:
    match = re.search(r"(\d+)", str(value))
    if match:
        return int(match.group(1))
    return 0


def _parse_float(value: str | float | None, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"[\d.]+", str(value))
    if match:
        try:
            return round(float(match.group()), 2)
        except ValueError:
            return default
    return default


def _number_to_chinese(num: float) -> str:
    if num <= 0:
        return "零元整"

    digits = ["零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖"]
    unit_chars = ["仟", "佰", "拾", ""]

    num_str = f"{num:.2f}"
    parts = num_str.split(".")
    integer_part = int(parts[0])
    decimal_part = int(parts[1])

    integer_str = ""
    temp = integer_part
    units_count = 0

    while temp > 0:
        digit = temp % 10
        if units_count < len(unit_chars):
            if digit > 0:
                integer_str = digits[digit] + unit_chars[units_count] + integer_str
            elif units_count > 0 and integer_str and integer_str[0] != "零":
                integer_str = "零" + integer_str
        temp //= 10
        units_count += 1

    integer_str = integer_str.rstrip("零")
    if not integer_str:
        integer_str = "零"

    if integer_part >= 10000:
        wan = integer_part // 10000
        wan_str = ""
        temp_wan = wan % 10000
        for i in range(3, -1, -1):
            d = (temp_wan // (10**i)) % 10 if i >= 0 else 0
            if i >= 0 and d > 0:
                wan_str = digits[d] + unit_chars[i] + wan_str
            elif i >= 0 and d == 0 and wan_str:
                wan_str = "零" + wan_str
        integer_str = wan_str + "万" + (integer_str.replace("零", "") if integer_str else "")

    result = integer_str + "元"

    if decimal_part == 0:
        result += "整"
    else:
        jiao = decimal_part // 10
        fen = decimal_part % 10
        if jiao > 0:
            result += digits[jiao] + "角"
        if fen > 0:
            result += digits[fen] + "分"
        if jiao == 0 and fen > 0:
            result = integer_str + "元零" + digits[fen] + "分"

    result = result.replace("零零", "零").replace("零元", "元")
    if result.endswith("元"):
        result += "整"

    return result


def _normalize_date(date_str: str) -> str:
    """将各种日期格式统一转换为 YYYY/MM/DD 格式"""
    date_str = date_str.strip()
    # 匹配各种日期格式：2026年04年14, 2026年04月14日，2026/04/14, 2026-04-14
    match = re.search(r"(\d{4})[年/\-](\d{1,2})[年月/\-](\d{1,2})[日]?", date_str)
    if match:
        year, month, day = match.groups()
        return f"{year}/{int(month):02d}/{int(day):02d}"
    return date_str


def _safe_contract_filename_stem(customer: str, *, max_len: int = 64) -> str:
    """去掉 Windows 非法文件名字符，避免生成/下载路径异常或并发覆盖。"""
    raw = (customer or "").strip()
    bad = '\\/:*?"<>|\n\r\t'
    cleaned = "".join(c for c in raw if c not in bad).strip(" .")
    return (cleaned or "客户")[:max_len]


def _resolve_model_number(
    raw_model: str,
    product_index: dict[str, dict[str, Any]],
) -> str:
    """
    解析输入型号到数据库中的可用型号。

    规则：
    1) 先做精确匹配（去空白后）。
    2) 若未命中，尝试“基础编号 -> 连字符后缀型号”唯一映射（如 7726 -> 7726-50f）。
       仅在候选唯一时自动纠正，避免误匹配。
    """
    model = "".join(str(raw_model or "").strip().split())
    if not model:
        return model
    if model in product_index:
        return model

    norm = model.lower()
    prefix = f"{norm}-"
    candidates: list[str] = []
    for db_model in product_index.keys():
        db_norm = db_model.lower()
        if db_norm.startswith(prefix):
            candidates.append(db_model)

    if len(candidates) == 1:
        corrected = candidates[0]
        logger.info("销售合同生成：型号自动纠正 %s -> %s", model, corrected)
        return corrected
    return model


def _pick_product_display_fields(
    *,
    input_name: str,
    input_spec: str,
    input_unit_price: str,
    db_product: dict[str, Any],
) -> tuple[str, str, float]:
    """
    选择展示/计算字段。

    规则：若型号能命中数据库，优先使用数据库里的名称/规格/价格；
    否则回退到请求内字段，保证“改编号后自动刷新产品信息”。
    """
    db_name = str(db_product.get("name") or "").strip()
    db_spec = str(db_product.get("specification") or db_product.get("spec") or "").strip()

    name = db_name or input_name
    spec = db_spec or input_spec

    if db_product.get("price") not in (None, ""):
        price = _parse_float(db_product.get("price", 0))
    elif input_unit_price and input_unit_price != "0":
        price = _parse_float(input_unit_price)
    else:
        price = 0.0

    return name, spec, price


def _get_output_dir() -> Path:
    import os

    ws = (os.environ.get("WORKSPACE_ROOT") or "").strip()
    if ws and os.path.isdir(ws):
        p = Path(ws).expanduser() / "uploads" / "sales_contracts"
    else:
        p = Path(__file__).resolve().parents[1] / "424" / "outputs" / "sales_contracts"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _resolve_excel_source_for_sales_contract_generation(
    requested_slug: str | None,
) -> tuple[Path, str | None]:
    """
    解析用于 ``fill_sales_contract_excel_template`` 的源模板路径。

    1. 按 ``requested_slug``（或库内默认）解析 ``document_templates``；若得到电子表格则用之。
    2. 若得到 Word（``.docx``）等非表格文件，则 **仅** 再解析送货单 Excel（``sales_delivery`` / 仓库 / 环境变量），
       避免 ``resolve_template_path_with_meta(slug='sales_delivery')`` 在缺行时回落到另一条 Word 路径。
    """
    from backend.document_template_service import (
        ROLE_SALES_CONTRACT,
        resolve_sales_delivery_excel_template_with_meta,
        resolve_template_path_with_meta,
    )
    from backend.sales_contract_excel_generate import is_sales_contract_excel_template_readable

    template_path, effective_id = resolve_template_path_with_meta(
        role=ROLE_SALES_CONTRACT,
        slug=requested_slug,
    )
    if not template_path:
        raise HTTPException(
            status_code=404,
            detail=(
                "未找到销售合同模板登记或磁盘文件：请在 document_templates 登记 "
                "role=sales_contract_docx，或设置 FHD_SALES_CONTRACT_TEMPLATE。"
            ),
        )

    suf = template_path.suffix.lower()
    if suf in (".xls", ".xlsx", ".xlsm") and is_sales_contract_excel_template_readable(template_path):
        return template_path, effective_id

    hint = ""
    if template_path.suffix.lower() == ".xls":
        hint = "（.xls 需 xlrd==1.2.0；xlrd>=2 无法读 BIFF8）"
    logger.warning(
        "销售合同生成：template_id=%s 解析为不可读模板 (%s)%s，改用送货单 Excel 源",
        requested_slug,
        template_path,
        hint,
    )
    excel_path, excel_id = resolve_sales_delivery_excel_template_with_meta()
    if not excel_path:
        raise HTTPException(
            status_code=404,
            detail=(
                "未找到 Excel 销售合同模板（送货单）：请在 document_templates 登记 "
                "slug=sales_delivery 且路径为 .xls/.xlsx，或将 424/document_templates/送货单.xls 放入仓库。"
            ),
        )
    return excel_path, excel_id


def _strip_trailing_chat_timestamp(text: str) -> str:
    """去掉消息末尾复制的时间戳（如 ``\\n15:29``），避免干扰 NL 抽取与客户校验。"""
    s = (text or "").strip()
    if not s:
        return s
    return re.sub(r"(?:\n\s*)+\d{1,2}:\d{2}(?::\d{2})?\s*$", "", s, flags=re.MULTILINE).strip()


def _product_row_to_bridge_dict(p: Any) -> dict[str, Any]:
    if p is None:
        return {}
    if isinstance(p, dict):
        d = dict(p)
    elif hasattr(p, "model_dump"):
        d = p.model_dump()
    else:
        d = {
            "model_number": getattr(p, "model_number", "") or "",
            "name": getattr(p, "name", "") or "",
            "spec": getattr(p, "spec", "") or "",
            "unit": getattr(p, "unit", "") or "",
            "quantity": getattr(p, "quantity", "") or "1",
            "unit_price": getattr(p, "unit_price", "") or "0",
            "amount": getattr(p, "amount", "") or "0",
        }
    return {
        "model_number": str(d.get("model_number") or "").strip(),
        "name": str(d.get("name") or "").strip(),
        "spec": str(d.get("spec") or "").strip(),
        "unit": str(d.get("unit") or "").strip(),
        "quantity": str(d.get("quantity") or "1"),
        "unit_price": str(d.get("unit_price") or "0"),
        "amount": str(d.get("amount") or "0"),
    }


def _product_model_sequence(products: Any) -> list[str]:
    out: list[str] = []
    for p in products or []:
        if isinstance(p, dict):
            out.append(str(p.get("model_number") or "").strip())
        else:
            out.append(str(getattr(p, "model_number", "") or "").strip())
    return out


def _maybe_apply_nl_bridge_to_generate_request(request: Any) -> None:
    """
    与 ``merge_planner_sales_contract_args`` 对齐：当前端把整段口语塞进 ``customer_name``、
    产品被拆成 ``PU``/``8`` 等碎片时，在生成前用 LLM+主数据重写请求。
    """
    from backend.sales_contract_intent_bridge import merge_planner_sales_contract_args

    raw = _strip_trailing_chat_timestamp(str(getattr(request, "customer_name", "") or ""))
    if raw != (getattr(request, "customer_name", "") or "").strip():
        request.customer_name = raw

    products_in = getattr(request, "products", None) or []
    args: dict[str, Any] = {
        "customer_name": raw,
        "products": [_product_row_to_bridge_dict(p) for p in products_in],
    }
    merged = merge_planner_sales_contract_args(dict(args), raw)
    new_cn = str(merged.get("customer_name") or "").strip()
    new_prods = merged.get("products") or []
    if not isinstance(new_prods, list) or not new_prods:
        return
    if new_cn == args["customer_name"] and _product_model_sequence(new_prods) == _product_model_sequence(
        args["products"]
    ):
        return

    from backend.routers.sales_contract import SalesContractProduct

    request.customer_name = new_cn or raw
    fixed: list[Any] = []
    for row in new_prods:
        if not isinstance(row, dict):
            continue
        fixed.append(
            SalesContractProduct(
                model_number=str(row.get("model_number") or "").strip(),
                name=str(row.get("name") or "").strip(),
                spec=str(row.get("spec") or "").strip(),
                unit=(str(row.get("unit") or "桶").strip() or "桶"),
                quantity=str(row.get("quantity") or "1"),
                unit_price=str(row.get("unit_price") or "0"),
                amount=str(row.get("amount") or "0"),
            )
        )
    if fixed:
        request.products = fixed
        logger.info("销售合同生成：已对口语整单应用 intent bridge，修正后产品行数=%s", len(fixed))


def run_sales_contract_generation(request: Any) -> dict[str, Any]:
    """
    执行生成；成功返回 ``{"success": True, "data": {...}, "message": "..."}``；
    模板缺失抛出 ``HTTPException(404)``；其它异常返回 ``success: False``。
    """
    from backend.contract_validator import validate_contract
    from backend.routers.xcagi_compat import _load_products_all_for_export
    from backend.shared_utils import extract_customer_name, find_matching_customer

    try:
        _maybe_apply_nl_bridge_to_generate_request(request)

        raw_customer = request.customer_name
        extracted = extract_customer_name(raw_customer)
        if extracted:
            matched_customer = find_matching_customer(extracted)
        else:
            matched_customer = find_matching_customer(raw_customer)

        if matched_customer:
            logger.info("模糊匹配客户：'%s' -> '%s'", raw_customer, matched_customer)
            request.customer_name = matched_customer

        logger.info(
            "销售合同生成：customer_name=%s, products_count=%s, template_id=%s",
            request.customer_name,
            len(request.products),
            request.template_id,
        )

        requested_slug = (request.template_id or "").strip() or None
        template_path, effective_template_id = _resolve_excel_source_for_sales_contract_generation(
            requested_slug
        )
        suffix = template_path.suffix.lower()
        logger.info("销售合同 Excel 生成：源模板=%s effective_id=%s", template_path, effective_template_id)

        try:
            all_products = _load_products_all_for_export(keyword=None, unit=None)
        except Exception as e:
            # 兼容异构库（如 is_active 列类型历史不一致）下的查询失败：保留生成能力，退化为仅使用请求内字段。
            logger.warning("销售合同生成：加载产品库失败，改用请求内产品字段：%s", e)
            all_products = []
        # 建立产品索引，清理型号中的空白字符
        product_index = {}
        for p in all_products:
            model = str(p.get("model_number", "")).strip()
            model_clean = "".join(model.split())  # 去除各种空白字符
            if model_clean:
                product_index[model_clean] = p

        products_data = []
        for p in request.products:
            qty = _parse_quantity(p.quantity)
            # 清理型号中的特殊字符和空格
            model_raw = str(p.model_number or "").strip()
            # 去除各种空白字符（空格、制表符、换行等）
            model = _resolve_model_number(model_raw, product_index)
            db_product = product_index.get(model, {})

            input_name = str(p.name or "").strip()
            input_spec = str(p.spec or "").strip()
            input_unit_price = str(p.unit_price or "").strip()
            name, spec, price = _pick_product_display_fields(
                input_name=input_name,
                input_spec=input_spec,
                input_unit_price=input_unit_price,
                db_product=db_product,
            )

            if p.unit and p.unit not in ["桶", "KG", "公斤", "克", "升", "毫升"]:
                unit = "桶"
            else:
                unit = p.unit or "桶"

            spec_quantity = 1.0
            if spec:
                match = re.search(
                    r"(\d+(?:\.\d+)?)\s*(KG|公斤 | 克 | 升 | 毫升 | 桶)", spec, re.IGNORECASE
                )
                if match:
                    spec_quantity = float(match.group(1))
                    unit_from_spec = match.group(2).upper()
                    if unit_from_spec == "KG":
                        unit = "KG"
                    elif unit_from_spec in ["公斤", "克", "升", "毫升", "桶"]:
                        unit = unit_from_spec

            amt = round(qty * spec_quantity * price, 2)
            total_weight = qty * spec_quantity

            products_data.append(
                {
                    "model_number": model,
                    "name": name,
                    "specification": spec,
                    "spec_quantity": spec_quantity,  # 从规格提取的数字，供公式计算
                    "unit": unit,
                    "quantity": str(qty),
                    "unit_price": str(price),
                    "amount": str(amt),
                    "total_weight": round(total_weight, 2),
                }
            )

        total_weight = sum(p.get("total_weight", 0) for p in products_data)
        total_amount = sum(_parse_float(p.get("amount", "0")) for p in products_data)
        total_amount_chinese = _number_to_chinese(total_amount)

        validation_result = validate_contract(request.customer_name, products_data)
        if not validation_result.get("valid"):
            logger.warning("合同校验失败：%s", validation_result)

        if not request.contract_date:
            request.contract_date = datetime.now().strftime("%Y/%m/%d")
        else:
            request.contract_date = _normalize_date(request.contract_date)

        template_data = {
            "customer_name": request.customer_name,
            "customer_phone": request.customer_phone,
            "contract_date": request.contract_date,
            "return_buckets_expected": str(request.return_buckets_expected),
            "return_buckets_actual": str(request.return_buckets_actual),
            "total_quantity": str(sum(_parse_quantity(p.quantity) for p in request.products)),
            "total_weight": f"{round(total_weight, 2)}KG",
            "total_amount": f"{round(total_amount, 2)}元",
            "total_amount_chinese": total_amount_chinese,
            "products": products_data,
        }

        output_dir = _get_output_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_stem = _safe_contract_filename_stem(request.customer_name)
        uniq = uuid.uuid4().hex[:8]

        from backend.sales_contract_excel_generate import fill_sales_contract_excel_template

        output_filename = f"销售合同_{safe_stem}_{timestamp}_{uniq}.xlsx"
        output_path = output_dir / output_filename
        fill_sales_contract_excel_template(template_path, template_data, output_path)

        logger.info("销售合同生成成功：%s", output_path)

        requested_tid = (getattr(request, "template_id", None) or "").strip() or None

        return {
            "success": True,
            "data": {
                "contract_id": str(uuid.uuid4()),
                "filename": output_filename,
                "file_path": str(output_path),
                "customer_name": request.customer_name,
                "contract_date": request.contract_date,
                "products": products_data,
                "total_quantity": sum(_parse_quantity(p.quantity) for p in request.products),
                "template_id": effective_template_id,
                "requested_template_id": requested_tid,
                "template_path_suffix": suffix,
                "export_format": "xlsx",
            },
            "message": "销售合同生成成功",
            "error": "",
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("销售合同生成失败：%s", e)
        return {
            "success": False,
            "data": None,
            "message": "销售合同生成失败",
            "error": str(e),
        }
