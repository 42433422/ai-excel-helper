from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher, get_close_matches
from typing import Dict, List, Optional, Tuple

try:
    from pypinyin import Style, pinyin
    _HAS_PYPINYIN = True
except Exception:
    Style = None  # type: ignore[assignment]
    pinyin = None  # type: ignore[assignment]
    _HAS_PYPINYIN = False

from app.db.models import PurchaseUnit


@dataclass(frozen=True)
class ResolvedPurchaseUnit:
    id: Optional[int]
    unit_name: str
    contact_person: str
    contact_phone: str
    address: str


def _to_pinyin(name: str) -> str:
    if not name:
        return ""
    if not _HAS_PYPINYIN:
        return str(name).lower()
    try:
        pinyins = pinyin(name, style=Style.NORMAL)
        return "".join(p[0] if p and p[0] else "" for p in pinyins)
    except Exception:
        return ""


def _to_first_letters(name: str) -> str:
    if not name:
        return ""
    if not _HAS_PYPINYIN:
        return "".join(ch for ch in str(name).lower() if ch.isalpha())
    try:
        pinyins = pinyin(name, style=Style.FIRST_LETTER)
        return "".join(p[0] if p and p[0] else "" for p in pinyins)
    except Exception:
        return ""


def _get_pinyin_parts(name: str) -> List[str]:
    if not name:
        return []
    if not _HAS_PYPINYIN:
        letters = "".join(ch for ch in str(name).lower() if ch.isalpha())
        return [letters] if letters else []
    try:
        pinyins = pinyin(name, style=Style.NORMAL)
        return [p[0] if p and p[0] else "" for p in pinyins if p and p[0]]
    except Exception:
        return []


def _pinyin_similarity(name1: str, name2: str) -> float:
    p1 = _to_pinyin(name1)
    p2 = _to_pinyin(name2)
    if not p1 or not p2:
        return 0.0
    return SequenceMatcher(None, p1, p2).ratio()


def _first_letter_match(input_fl: str, target_fl: str) -> bool:
    if not input_fl or not target_fl:
        return False
    input_clean = re.sub(r'[^a-z]', '', input_fl.lower())
    target_clean = re.sub(r'[^a-z]', '', target_fl.lower())
    if not input_clean or not target_clean:
        return False
    if input_clean == target_clean:
        return True
    if len(input_clean) >= 2 and len(target_clean) >= 2:
        if input_clean[:2] == target_clean[:2]:
            return True
    return False


def resolve_purchase_unit(input_unit: str) -> Optional[ResolvedPurchaseUnit]:
    from app.db.session import get_db

    name = (input_unit or "").strip()
    if not name:
        return None

    with get_db() as db:
        customers = db.query(PurchaseUnit).all()
        customer_names = [c.unit_name for c in customers if getattr(c, "unit_name", None)]

        pinyin_map: Dict[str, Tuple[str, List[str], str]] = {}
        for cn in customer_names:
            pinyin_map[cn] = (_to_pinyin(cn), _get_pinyin_parts(cn), _to_first_letters(cn))

        input_pinyin = _to_pinyin(name)
        input_parts = _get_pinyin_parts(name)
        input_fl = _to_first_letters(name)

        best_match: Optional[Tuple[str, float]] = None

        for cn, (pinyin_str, parts, fl) in pinyin_map.items():
            fl_match = _first_letter_match(input_fl, fl)

            if fl_match and len(input_parts) == len(parts):
                for ip, cp in zip(input_parts, parts):
                    if ip and cp and (ip[0] == cp[0] or ip.startswith(cp[:1]) or cp.startswith(ip[:1])):
                        similarity = _pinyin_similarity(name, cn)
                        if best_match is None or similarity > best_match[1]:
                            best_match = (cn, similarity)

            if input_pinyin == pinyin_str:
                similarity = _pinyin_similarity(name, cn)
                if best_match is None or similarity > best_match[1]:
                    best_match = (cn, similarity)

            if input_parts and parts:
                common_parts = 0
                for ip in input_parts:
                    for cp in parts:
                        if ip and cp and (ip.startswith(cp[:2]) or cp.startswith(ip[:2])):
                            common_parts += 1
                            break
                if common_parts >= min(len(input_parts), len(parts)) * 0.5:
                    similarity = _pinyin_similarity(name, cn)
                    if best_match is None or similarity > best_match[1]:
                        best_match = (cn, similarity)

        exact = next((c for c in customers if c.unit_name == name), None)
        if exact:
            return ResolvedPurchaseUnit(
                id=exact.id,
                unit_name=exact.unit_name,
                contact_person=exact.contact_person or "",
                contact_phone=exact.contact_phone or "",
                address=exact.address or "",
            )

        for cand in sorted(customer_names, key=len, reverse=True):
            if name in cand:
                c = next((x for x in customers if x.unit_name == cand), None)
                if c:
                    return ResolvedPurchaseUnit(
                        id=c.id,
                        unit_name=c.unit_name,
                        contact_person=c.contact_person or "",
                        contact_phone=c.contact_phone or "",
                        address=c.address or "",
                    )

        if best_match and best_match[1] >= 0.4:
            c = next((x for x in customers if x.unit_name == best_match[0]), None)
            if c:
                return ResolvedPurchaseUnit(
                    id=c.id,
                    unit_name=c.unit_name,
                    contact_person=c.contact_person or "",
                    contact_phone=c.contact_phone or "",
                    address=c.address or "",
                )

        matches = get_close_matches(name, customer_names, n=1, cutoff=0.5)
        if matches:
            c = next((x for x in customers if x.unit_name == matches[0]), None)
            if c:
                return ResolvedPurchaseUnit(
                    id=c.id,
                    unit_name=c.unit_name,
                    contact_person=c.contact_person or "",
                    contact_phone=c.contact_phone or "",
                    address=c.address or "",
                )

    return None
