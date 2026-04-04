"""
电话业务员：订购场景固定话术与简单状态机。

在意图无法命中时引导「购买单位 → 订什么 → 复述」，并可选用产品库 / 购买单位库做补全。
"""

from __future__ import annotations

import logging
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 听不清 / 是否在听 等（简繁常见说法）
_CONNECTIVITY_PATTERNS = re.compile(
    r"(没|沒|听不|聽不|听不见|聽不見|听不到|聽不到|听得到|聽得到|能听到|能聽到|听见|聽見)"
    r"|(说[话話]|說[话話]|麦克风|麥克風|麦|麥|声音|聲音|信号|訊號)"
    r"|(喂|哈喽|哈囉|hello)",
    re.IGNORECASE,
)


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _looks_like_connectivity_complaint(text: str) -> bool:
    t = (text or "").strip()
    if len(t) < 2:
        return False
    if _CONNECTIVITY_PATTERNS.search(t):
        return True
    if any(
        x in t
        for x in (
            "听得见吗",
            "聽得見嗎",
            "能听到吗",
            "能聽到嗎",
            "听得到吗",
            "聽得到嗎",
            "我说话",
            "我說話",
            "你说",
            "你說",
        )
    ):
        return True
    return False


def _load_purchase_unit_names() -> List[str]:
    try:
        from app.db import SessionLocal
        from app.db.models import PurchaseUnit

        session = SessionLocal()
        try:
            rows = (
                session.query(PurchaseUnit.unit_name)
                .filter(PurchaseUnit.is_active == True)  # noqa: E712
                .all()
            )
            return sorted({(r[0] or "").strip() for r in rows if (r[0] or "").strip()})
        finally:
            session.close()
    except Exception as e:
        logger.debug("purchase unit list unavailable: %s", e)
        return []


def _best_unit_match(spoken: str, names: List[str]) -> Tuple[Optional[str], List[str]]:
    """返回 (最佳匹配名, 若干候选)。"""
    s = _normalize(spoken)
    if not s or not names:
        return None, []
    hits: List[str] = []
    for n in names:
        if not n:
            continue
        if n in s or s in n:
            hits.append(n)
    if not hits:
        for n in names:
            if len(n) >= 2 and any(
                s[i : i + len(n)] == n for i in range(max(0, len(s) - len(n) + 1))
            ):
                hits.append(n)
    if not hits:
        return None, []
    hits = list(dict.fromkeys(hits))
    hits.sort(key=len, reverse=True)
    return hits[0], hits[:3]


def _looks_like_order_fragment(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    keys = (
        "桶",
        "箱",
        "件",
        "吨",
        "公斤",
        "千克",
        "规格",
        "型号",
        "下单",
        "订货",
        "订",
        "要货",
        "出货",
        "发货",
        "×",
        "*",
        "x",
        "X",
    )
    if any(k in t for k in keys):
        return True
    if re.search(r"\d+\s*[桶箱件]", t):
        return True
    if re.search(r"(?:规格|型号)\s*[:：]?\s*[\d.]+", t):
        return True
    return bool(re.search(r"\b[0-9A-Z][0-9A-Z-]{3,}\b", t.upper()))


def _extract_model_tokens(text: str) -> List[str]:
    raw = (text or "").upper()
    found = re.findall(r"\b[0-9A-Z][0-9A-Z-]{2,}\b", raw)
    out: List[str] = []
    for x in found:
        if re.fullmatch(r"(API|HTTP|JSON|XML|USB|PDF)", x):
            continue
        if x not in out:
            out.append(x)
    return out[:5]


def _product_preview_for_recap(unit_name: str, order_text: str) -> str:
    lines: List[str] = []
    try:
        from app.bootstrap import get_products_service
        from app.utils.ai_helpers import format_money, safe_float

        svc = get_products_service()
        models = _extract_model_tokens(order_text)
        seen: set[str] = set()
        for m in models:
            if m in seen:
                continue
            seen.add(m)
            r = svc.get_products(
                unit_name=unit_name or None,
                model_number=m,
                keyword=None,
                page=1,
                per_page=3,
            )
            rows = (r or {}).get("data") or []
            for row in rows[:2]:
                mn = (row.get("model_number") or row.get("product_code") or "").strip()
                nm = (row.get("name") or row.get("product_name") or "-").strip()
                pr = safe_float(row.get("price"))
                lines.append(f"{mn or m}，{nm}，参考价￥{format_money(pr)}")
        if not lines and order_text:
            r2 = svc.get_products(
                unit_name=unit_name or None,
                model_number=None,
                keyword=order_text[:40] or None,
                page=1,
                per_page=3,
            )
            rows2 = (r2 or {}).get("data") or []
            for row in rows2[:3]:
                mn = (row.get("model_number") or "").strip()
                nm = (row.get("name") or row.get("product_name") or "-").strip()
                pr = safe_float(row.get("price"))
                lines.append(f"{mn or '-'}，{nm}，参考价￥{format_money(pr)}")
    except Exception as e:
        logger.debug("product recap query failed: %s", e)
    if not lines:
        return ""
    return "库里相近产品：" + "；".join(lines[:4]) + "。"


class PhoneSalesDialog:
    """一通电话内的订购引导状态（线程安全）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._unit_raw: str = ""
        self._unit_resolved: str = ""
        self._order_line: str = ""
        self._stashed_order: str = ""
        self._unit_prompted: bool = False
        self._unit_names_cache: Optional[List[str]] = None

    def reset(self) -> None:
        with self._lock:
            self._unit_raw = ""
            self._unit_resolved = ""
            self._order_line = ""
            self._stashed_order = ""
            self._unit_prompted = False

    def _ensure_unit_names(self) -> List[str]:
        if self._unit_names_cache is None:
            self._unit_names_cache = _load_purchase_unit_names()
        return self._unit_names_cache

    @staticmethod
    def should_handle_unknown(intent_result: Optional[Dict[str, Any]]) -> bool:
        """是否走本模块（未知/弱意图），已识别的问候、再见、业务意图不走。"""
        if not intent_result:
            return True
        if intent_result.get("is_greeting") or intent_result.get("is_goodbye"):
            return False
        if intent_result.get("is_help") or intent_result.get("is_negated"):
            return False
        pi = (intent_result.get("primary_intent") or "").lower()
        if any(k in pi for k in ("product", "shipment", "order", "inventory", "stock")):
            return False
        return True

    def reply(self, asr_text: str, intent_result: Optional[Dict[str, Any]]) -> str:
        text = _normalize(asr_text)
        if not text:
            return "不好意思，我没听清，麻烦您再说一下购买单位和订货内容好吗？"

        with self._lock:
            if _looks_like_connectivity_complaint(text):
                return (
                    "不好意思，我这边能听见。为免耽误您时间，请先告诉我贵司或购买单位名称，"
                    "再说一下想订的产品、数量或型号，我帮您记下来并核对。"
                )

            if intent_result and intent_result.get("is_goodbye"):
                self._unit_raw = ""
                self._unit_resolved = ""
                self._order_line = ""
                self._stashed_order = ""
                self._unit_prompted = False

            if not self._should_handle_locked(intent_result):
                return ""

            if not self._unit_raw:
                if _looks_like_order_fragment(text):
                    self._stashed_order = text
                    self._unit_prompted = True
                    return (
                        "请问您是哪个购买单位或客户名称？"
                        "您刚才说的订货内容我先帮您记着，等您说完单位后我一并复述确认。"
                    )
                self._unit_raw = text
                names = self._ensure_unit_names()
                best, cands = _best_unit_match(text, names)
                self._unit_resolved = best or text
                hint = ""
                if best and best != text:
                    hint = f"我按「{best}」记在系统单位库里了。"
                elif cands and not best:
                    hint = f"单位名不太确定，先按您说的记；若不对请纠正（库里类似：{'、'.join(cands)}）。"
                if self._stashed_order:
                    ol = self._stashed_order
                    self._order_line = ol
                    self._stashed_order = ""
                    self._unit_prompted = False
                    db_bit = _product_preview_for_recap(self._unit_resolved or self._unit_raw, ol)
                    u = self._unit_resolved or self._unit_raw
                    tail = (
                        f"{hint}"
                        f"我跟您复述一下：购买单位「{u}」，订货需求「{ol}」。"
                        f"{db_bit}"
                        f"如有不对请直接说。还需要查价格或库存吗？"
                    )
                    return tail
                q = "好的，请问需要订购什么产品、数量或规格型号？"
                return f"{hint}{q}" if hint else q

            if not self._order_line:
                self._order_line = text
                db_bit = _product_preview_for_recap(self._unit_resolved or self._unit_raw, text)
                u = self._unit_resolved or self._unit_raw
                core = (
                    f"我跟您复述一下：购买单位「{u}」，订货需求「{text}」。"
                    f"{db_bit}"
                    f"如有不对请直接说，我可以帮您改。还需要查价格或库存吗？"
                )
                return core

            # 已复述后：补充说明当作更新订货行
            self._order_line = text
            db_bit = _product_preview_for_recap(self._unit_resolved or self._unit_raw, text)
            u = self._unit_resolved or self._unit_raw
            return f"已按您最新说法更新为：单位「{u}」，需求「{text}」。{db_bit}还需要别的吗？"

    def _should_handle_locked(self, intent_result: Optional[Dict[str, Any]]) -> bool:
        return self.should_handle_unknown(intent_result)
