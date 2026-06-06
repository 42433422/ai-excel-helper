"""模型支付订单：本地 JSON 落盘，供异步通知幂等更新（沙箱/单机够用，生产请换数据库）。"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_lock = threading.Lock()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def order_store_path() -> Path:
    custom = (os.environ.get("MODEL_PAYMENT_ORDER_STORE_PATH") or "").strip()
    if custom:
        return Path(custom)
    return _repo_root() / "data" / "model_payment_orders.json"


def _utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def _empty_state() -> dict[str, Any]:
    return {"orders": {}, "entitlements": {}}


def _load() -> dict[str, Any]:
    p = order_store_path()
    if not p.is_file():
        return _empty_state()
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return _empty_state()
            data.setdefault("orders", {})
            if not isinstance(data["orders"], dict):
                data["orders"] = {}
            data.setdefault("entitlements", {})
            if not isinstance(data["entitlements"], dict):
                data["entitlements"] = {}
            return data
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("读取订单文件失败，将使用空表: %s", e)
        return _empty_state()


def _atomic_write(p: Path, payload: dict[str, Any]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(body)
    os.replace(tmp, p)


def record_checkout_pending(
    *,
    out_trade_no: str,
    plan_id: str,
    amount_cents: int,
    amount_yuan: str,
) -> None:
    """预下单成功后写入待支付订单。"""
    with _lock:
        data = _load()
        orders: dict[str, Any] = data["orders"]
        orders[out_trade_no] = {
            "out_trade_no": out_trade_no,
            "plan_id": plan_id,
            "amount_cents": int(amount_cents),
            "amount_yuan": amount_yuan,
            "status": "pending_payment",
            "trade_no": None,
            "created_at": _utc_iso(),
            "paid_at": None,
            "notify_count": 0,
            "last_notify_at": None,
        }
        _atomic_write(order_store_path(), data)
    logger.info("[model-payment] order pending out_trade_no=%s plan_id=%s", out_trade_no, plan_id)


def apply_notify_paid(
    *,
    out_trade_no: str,
    trade_no: str,
    total_amount: str,
) -> tuple[str, dict[str, Any] | None]:
    """
    验签通过后调用：金额一致则置为 paid，重复通知幂等。

    返回 (reason, order_snapshot)；reason 取值：
    marked_paid | already_paid | unknown_order | amount_mismatch
    """
    with _lock:
        data = _load()
        orders: dict[str, Any] = data["orders"]
        o = orders.get(out_trade_no)
        if not o:
            logger.warning("[model-payment] notify: 未知 out_trade_no=%s", out_trade_no)
            return "unknown_order", None

        try:
            expected_yuan = f"{int(o['amount_cents']) / 100:.2f}"
        except (TypeError, ValueError, KeyError):
            expected_yuan = str(o.get("amount_yuan") or "")

        if total_amount != expected_yuan:
            logger.warning(
                "[model-payment] notify: 金额不一致 out_trade_no=%s expected=%s got=%s",
                out_trade_no,
                expected_yuan,
                total_amount,
            )
            return "amount_mismatch", dict(o)

        now = _utc_iso()
        if o.get("status") == "paid":
            o["notify_count"] = int(o.get("notify_count") or 0) + 1
            o["last_notify_at"] = now
            _atomic_write(order_store_path(), data)
            return "already_paid", dict(o)

        o["notify_count"] = int(o.get("notify_count") or 0) + 1
        o["last_notify_at"] = now
        o["status"] = "paid"
        o["trade_no"] = trade_no
        o["paid_at"] = now

        plan_id = str(o.get("plan_id") or "")
        ent_snapshot: dict[str, Any] | None = None
        if plan_id:
            ent_snapshot = _grant_entitlement_inplace(
                data,
                plan_id=plan_id,
                out_trade_no=out_trade_no,
                trade_no=trade_no,
                paid_at=now,
            )

        snap = dict(o)
        if ent_snapshot is not None:
            snap["entitlement"] = ent_snapshot
        _atomic_write(order_store_path(), data)
        logger.info(
            "[model-payment] order paid out_trade_no=%s trade_no=%s plan_id=%s purchase_count=%s",
            out_trade_no,
            trade_no,
            plan_id,
            (ent_snapshot or {}).get("purchase_count"),
        )
        return "marked_paid", snap


def _grant_entitlement_inplace(
    data: dict[str, Any],
    *,
    plan_id: str,
    out_trade_no: str,
    trade_no: str,
    paid_at: str,
) -> dict[str, Any]:
    """在同一份 data 上累加一次已购权益。调用方负责最终 _atomic_write。"""
    ents: dict[str, Any] = data.setdefault("entitlements", {})
    cur = ents.get(plan_id) or {}
    purchase_count = int(cur.get("purchase_count") or 0) + 1
    record = {
        "plan_id": plan_id,
        "purchase_count": purchase_count,
        "first_paid_at": cur.get("first_paid_at") or paid_at,
        "last_paid_at": paid_at,
        "last_out_trade_no": out_trade_no,
        "last_trade_no": trade_no,
    }
    ents[plan_id] = record
    return dict(record)


def list_entitlements() -> list[dict[str, Any]]:
    """返回已购权益（按 last_paid_at 倒序）。"""
    with _lock:
        data = _load()
    ents: dict[str, Any] = data.get("entitlements") or {}
    items = [dict(v) for v in ents.values() if isinstance(v, dict)]
    items.sort(key=lambda r: str(r.get("last_paid_at") or ""), reverse=True)
    return items


def get_entitlement(plan_id: str) -> dict[str, Any] | None:
    """按 plan_id 查已购记录；未购返回 None。"""
    if not plan_id:
        return None
    with _lock:
        data = _load()
    ents: dict[str, Any] = data.get("entitlements") or {}
    record = ents.get(plan_id)
    if isinstance(record, dict):
        return dict(record)
    return None


def get_order(out_trade_no: str) -> dict[str, Any] | None:
    """读取本地订单记录快照。"""
    if not out_trade_no:
        return None
    with _lock:
        data = _load()
    o = (data.get("orders") or {}).get(out_trade_no)
    return dict(o) if isinstance(o, dict) else None


def update_order_status(
    *,
    out_trade_no: str,
    status: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """原地更新订单状态（closed / refunded 等）。找不到返回 None。"""
    if not out_trade_no:
        return None
    with _lock:
        data = _load()
        orders: dict[str, Any] = data.setdefault("orders", {})
        o = orders.get(out_trade_no)
        if not isinstance(o, dict):
            return None
        o["status"] = status
        o["updated_at"] = _utc_iso()
        if extra:
            o.update(extra)
        _atomic_write(order_store_path(), data)
        return dict(o)
