"""
销售合同：单次 LLM 结构化抽取 + 主数据对齐。

供 UnifiedOrchestrator、Planner 工具链、``user_input_parser.extract_structured_info`` 共用。
"""

from __future__ import annotations

import json
import logging
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Mapping

logger = logging.getLogger(__name__)

_thread_local = threading.local()

_EXTRACT_SYS = """你是销售合同信息抽取器。只输出一个 JSON 对象，不要 markdown，不要解释。

JSON 结构（键名固定）：
{
  "customer_hint": string | null,
  "lines": [
    {
      "model_hint": string | null,
      "name_hint": string | null,
      "quantity": number,
      "unit": string | null
    }
  ]
}

规则：
1) customer_hint：用户口语里的店名/单位名片段（如「惠州市丰驰家居」），不要编造「有限公司」等全称；读不到填 null。
2) lines：每条订货一行；quantity 为阿拉伯数字；读不到数量则填 1。
3) model_hint 与 name_hint 不要混在同一字段：纯编号/字母数字型号放 model_hint；中文品名放 name_hint。勿仅用过短字母片段作 model_hint；「PU稀释剂」应放在 name_hint。
4) 忽略「帮我打印」「销售合同」等指令性废话，不要写进 customer_hint；切勿把整句用户话写入 customer_hint。
5) 「一统」「一彤」视为「一桶」之误写：如「一统308」表示一桶型号 308（quantity=1，model_hint 为 308）。
"""


@dataclass
class DraftLine:
    model_hint: str | None = None
    name_hint: str | None = None
    quantity: float = 1.0
    unit: str | None = None


@dataclass
class SalesContractDraft:
    customer_hint: str | None = None
    lines: list[DraftLine] = field(default_factory=list)


def set_planner_contract_user_utterance(text: str | None) -> None:
    """Planner 单轮入口设置当前用户原话，供 ``sales_contract_export`` 启发式修复。"""
    _thread_local.planner_user_utterance = text


def get_planner_contract_user_utterance() -> str | None:
    return getattr(_thread_local, "planner_user_utterance", None)


def message_suggests_sales_contract(user_message: str) -> bool:
    msg = (user_message or "").strip()
    if not msg:
        return False
    if "销售合同" in msg or "购销合同" in msg:
        return True
    if "合同" in msg and ("桶" in msg or "瓶" in msg or "箱" in msg):
        return True
    return False


def sales_contract_utterance_requires_structured_llm(user_message: str) -> bool:
    """
    判断是否为「口语化、多品、叙事型」销售合同订货，**应以单次 LLM 结构化抽取为主**，
    不宜在抽取失败后再用正则/子串规则去猜型号（易错、与「明码短句」混淆）。

    短句、已明确「单位全称 + 型号 + 桶数」等可走规则降级（见 ``extract_structured_info``）。
    """
    m = (user_message or "").strip()
    if len(m) < 20:
        return False
    if not message_suggests_sales_contract(m):
        return False
    oral = (
        "那个",
        "帮我",
        "还有",
        "以及",
        "再来",
        "一瓶",
        "一桶",
        "一统",
        "慢干",
        "稀释",
        "销售合同",
        "购销合同",
        "呃",
        "打印",
        "生成",
    )
    hits = sum(1 for k in oral if k in m)
    if len(m) >= 28 and hits >= 2:
        return True
    if len(m) >= 20 and hits >= 3:
        return True
    if len(m) >= 24 and (m.count("桶") + m.count("瓶") >= 2):
        return True
    if (m.count("，") + m.count(",")) >= 2 and ("合同" in m or "桶" in m or "瓶" in m):
        return True
    return False


def _compact(s: str) -> str:
    return "".join((s or "").strip().lower().split())


# 与 ``slot_filler.SlotFiller._normalize_order_typos`` 对齐，减轻「一统→一桶」类误写对抽取的干扰
_CONTRACT_TYPO_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("一统", "一桶"),
    ("一彤", "一桶"),
    ("两统", "两桶"),
    ("三统", "三桶"),
    ("四统", "四桶"),
    ("五统", "五桶"),
)


def _normalize_contract_input_typos(text: str) -> str:
    s = text
    for a, b in _CONTRACT_TYPO_REPLACEMENTS:
        s = s.replace(a, b)
    return s


def _customer_hint_is_bulk_user_utterance(hint: str | None) -> bool:
    """模型把整句塞进 customer_hint 时，勿对其做模糊客户匹配。"""
    h = (hint or "").strip()
    if not h:
        return False
    if len(h) > 32:
        return True
    noise = ("销售合同", "帮我", "打印", "生成", "桶", "瓶", "稀释剂", "慢干")
    if len(h) > 16 and sum(1 for k in noise if k in h) >= 3:
        return True
    return False


def _parse_draft_from_json(data: dict[str, Any]) -> SalesContractDraft:
    hint = data.get("customer_hint")
    if hint is not None:
        hint = str(hint).strip() or None
    raw_lines = data.get("lines") or data.get("items") or []
    lines: list[DraftLine] = []
    if isinstance(raw_lines, list):
        for row in raw_lines:
            if not isinstance(row, dict):
                continue
            mh = row.get("model_hint")
            nh = row.get("name_hint")
            if mh is not None:
                mh = str(mh).strip() or None
            if nh is not None:
                nh = str(nh).strip() or None
            try:
                qty = float(row.get("quantity", 1) or 1)
            except (TypeError, ValueError):
                qty = 1.0
            if qty <= 0:
                qty = 1.0
            unit = row.get("unit")
            if unit is not None:
                unit = str(unit).strip() or None
            lines.append(DraftLine(model_hint=mh, name_hint=nh, quantity=qty, unit=unit))
    return SalesContractDraft(customer_hint=hint, lines=lines)


def _strip_json_fences(text: str) -> str:
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```\s*$", "", t)
    return t.strip()


def extract_sales_contract_draft(user_message: str) -> SalesContractDraft | None:
    """
    单次同步 LLM 调用；失败返回 None。
    优先 ``response_format=json_object``，不支持则降级为普通 JSON 文本。
    """
    text = _normalize_contract_input_typos((user_message or "").strip())
    if not text:
        return None
    try:
        from backend.llm_config import get_llm_client, require_api_key, resolve_chat_model

        require_api_key()
    except Exception as e:
        logger.debug("[sales_contract_bridge] skip extract: %s", e)
        return None

    client = get_llm_client()
    model = resolve_chat_model()
    user_block = f"用户输入：\n{text}"

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": _EXTRACT_SYS},
            {"role": "user", "content": user_block},
        ],
        "temperature": 0.1,
        "max_tokens": 900,
    }

    content = ""
    try:
        kwargs_rf = dict(kwargs)
        kwargs_rf["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(**kwargs_rf)
        content = (resp.choices[0].message.content or "").strip()
    except TypeError:
        resp = client.chat.completions.create(**kwargs)
        content = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        logger.info("[sales_contract_bridge] json_object path failed: %s", e)
        try:
            resp = client.chat.completions.create(**kwargs)
            content = (resp.choices[0].message.content or "").strip()
        except Exception as e2:
            logger.warning("[sales_contract_bridge] extract failed: %s", e2)
            return None

    try:
        data = json.loads(_strip_json_fences(content))
    except json.JSONDecodeError:
        logger.warning("[sales_contract_bridge] invalid JSON from model")
        return None
    if not isinstance(data, dict):
        return None
    draft = _parse_draft_from_json(data)
    if not draft.lines and not draft.customer_hint:
        return None
    return draft


def resolve_draft_to_tool_slots(
    draft: SalesContractDraft,
    raw_user_message: str | None = None,
) -> dict[str, Any] | None:
    """
    将 draft 解析为工具槽位：
    ``{"customer_name": str, "products": [{"model_number", "name", "quantity", ...}]}``。

    ``raw_user_message``：用户原话；用于修复错拆型号、以及当 ``customer_hint`` 为整句时从原文解析店名。
    """
    from backend.product_db_read import find_matching_customer_unified
    from backend.routers.xcagi_compat import _load_products_all_for_export
    from backend.sales_contract_generate_core import _resolve_model_number

    raw = _normalize_contract_input_typos((raw_user_message or "").strip())

    try:
        rows = _load_products_all_for_export(keyword=None, unit=None)
    except Exception as e:
        logger.warning("[sales_contract_bridge] load products failed: %s", e)
        rows = []

    product_index: dict[str, dict[str, Any]] = {}
    for p in rows or []:
        model = str(p.get("model_number") or "").strip()
        model_clean = "".join(model.split())
        if model_clean:
            product_index[model_clean] = p

    customer_out = ""
    if draft.customer_hint and not _customer_hint_is_bulk_user_utterance(draft.customer_hint):
        hit = find_matching_customer_unified(draft.customer_hint)
        customer_out = (hit or draft.customer_hint).strip()

    if not customer_out and raw:
        from backend.shared_utils import extract_customer_name

        spoken = extract_customer_name(raw)
        if spoken:
            customer_out = (find_matching_customer_unified(spoken) or spoken).strip()

    from backend.sales_contract_product_match import match_product_row_for_sales_contract

    products_out: list[dict[str, Any]] = []
    all_product_rows = list(rows or [])

    for line in draft.lines:
        matched = match_product_row_for_sales_contract(
            name_hint=line.name_hint,
            model_hint=line.model_hint,
            all_rows=all_product_rows,
            product_index=product_index,
            resolve_model_number=_resolve_model_number,
        )
        if not matched:
            continue
        resolved_model, db_row = matched

        qty = max(1, int(line.quantity))
        unit = (line.unit or db_row.get("unit") or "桶")
        unit = str(unit).strip() or "桶"
        products_out.append(
            {
                "model_number": resolved_model,
                "name": str(db_row.get("name") or ""),
                "spec": str(db_row.get("specification") or db_row.get("spec") or ""),
                "unit": unit,
                "unit_price": str(db_row.get("price", 0)),
                "quantity": str(qty),
            }
        )

    if not products_out:
        return None
    if not customer_out:
        customer_out = (draft.customer_hint or "").strip() or "客户"

    return {"customer_name": customer_out, "products": products_out}


def resolve_draft_to_extract_structured_dict(
    draft: SalesContractDraft, *, raw_message: str | None = None
) -> dict[str, Any] | None:
    """与 ``user_input_parser.extract_structured_info`` 返回形状兼容。"""
    slots = resolve_draft_to_tool_slots(draft, raw_user_message=raw_message)
    if not slots:
        return None
    products_rows = slots.get("products") or []
    quantities: dict[str, int] = {}
    prod_keys: list[str] = []
    for p in products_rows:
        if not isinstance(p, dict):
            continue
        m = str(p.get("model_number") or "").strip()
        if not m:
            continue
        prod_keys.append(m)
        try:
            quantities[m] = int(p.get("quantity", 1))
        except (TypeError, ValueError):
            quantities[m] = 1
    return {
        "customer_name": slots.get("customer_name"),
        "products": prod_keys,
        "quantities": quantities,
        "raw_message": raw_message,
    }


def _coerce_planner_bridge_utterance(args: Mapping[str, Any], user_message: str | None) -> str | None:
    """
    Planner 合并用：优先显式 user_message；否则若模型把整单塞进 ``customer_name``
    （并行线程下 threading.local 常为空），则用该字段作 LLM 抽取输入。
    """
    um = (user_message or "").strip() or None
    if um:
        return um
    cn = str(args.get("customer_name") or "").strip()
    # 典型整句约 28–40 字；阈值过高会导致并行线程下无法把整句当作抽取输入
    if len(cn) > 22 and ("销售合同" in cn or "合同" in cn) and ("桶" in cn or "瓶" in cn):
        return cn
    return None


def sales_contract_tool_args_need_bridge(args: Mapping[str, Any], utterance: str | None) -> bool:
    """启发式：整句客户名或产品行损坏时，用 utterance 跑 bridge。"""
    um = (utterance or "").strip()
    if not um:
        return False
    cn = str(args.get("customer_name") or "").strip()
    if len(cn) > 48:
        return True
    noise = ("销售合同", "帮我", "打印", "生成", "桶", "瓶")
    if len(cn) > 14 and sum(1 for k in noise if k in cn) >= 3:
        return True
    products = args.get("products") or []
    if not isinstance(products, list) or not products:
        return True
    empty_model = 0
    for p in products:
        if not isinstance(p, dict):
            empty_model += 1
            continue
        if not str(p.get("model_number") or "").strip():
            empty_model += 1
    return empty_model >= len(products)


def merge_planner_sales_contract_args(
    args: dict[str, Any],
    user_message: str | None,
) -> dict[str, Any]:
    """
    用 bridge（LLM 抽取 + 主数据对齐）覆盖 ``customer_name`` / ``products``。

    - **损坏参数**（整句客户名、空型号等）：始终合并。
    - **口语长单**（``sales_contract_utterance_requires_structured_llm``）：以用户原话为准再抽一轮，
      避免模型直接带参调导出 API 却未结构化。
    """
    out = dict(args)
    um = (out.pop("__user_message", None) or "").strip() or None
    um = um or _coerce_planner_bridge_utterance(out, user_message)
    if not um:
        return out
    need = sales_contract_tool_args_need_bridge(out, um)
    prefer_llm = sales_contract_utterance_requires_structured_llm(um)
    if not need and not prefer_llm:
        return out
    draft = extract_sales_contract_draft(um)
    if not draft:
        return out
    slots = resolve_draft_to_tool_slots(draft, raw_user_message=um)
    if not slots:
        return out
    out["customer_name"] = slots["customer_name"]
    out["products"] = slots["products"]
    return out


def _prefill_customer_from_raw_when_entities_bad(merged: dict[str, Any], user_message: str) -> None:
    """无 LLM 或 customer 槽为整句时，用语义规则从原文解析客户并写回 ``merged``。"""
    cn = str(merged.get("customer_name") or "").strip()
    if cn and not _customer_hint_is_bulk_user_utterance(cn):
        return
    try:
        from backend.shared_utils import extract_customer_name
        from backend.product_db_read import find_matching_customer_unified

        spoken = extract_customer_name(user_message)
        if spoken:
            hit = find_matching_customer_unified(spoken)
            if hit:
                merged["customer_name"] = hit
    except Exception:
        logger.debug("[merge_bridge] customer fallback skipped", exc_info=True)


def merge_bridge_prefill_entities(
    intent: str,
    entities: dict[str, Any],
    user_message: str,
) -> dict[str, Any]:
    """Orchestrator：在 sales_contract 意图下用 LLM+resolve 预填 entities。"""
    merged = dict(entities or {})
    if intent != "sales_contract":
        return merged
    if not message_suggests_sales_contract(user_message):
        return merged
    try:
        from backend.llm_config import require_api_key

        require_api_key()
    except Exception:
        _prefill_customer_from_raw_when_entities_bad(merged, user_message)
        return merged
    draft = extract_sales_contract_draft(user_message)
    if not draft:
        return merged
    slots = resolve_draft_to_tool_slots(draft, raw_user_message=user_message)
    if not slots:
        return merged
    merged["customer_name"] = slots["customer_name"]
    merged["products"] = slots["products"]
    return merged
