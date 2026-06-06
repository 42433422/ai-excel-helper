"""模型支付页（Vue ModelPaymentView）兼容 API：演示套餐与支付宝预下单。"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Body, Header, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from app.infrastructure.payment import alipay as mp_ali
from app.infrastructure.payment import order_store as mp_orders
from app.infrastructure.payment.payment_sot import (
    MODEL_PAYMENT_JSON_DEPRECATED_AFTER,
    is_fhd_postgres_payment_sot,
    is_json_legacy_payment_sot,
    is_local_model_payment_sot,
    is_modstore_payment_sot,
    model_payment_backend,
    modstore_payment_hint,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/model-payment", tags=["model-payment"])

# 与前端 ModelPaymentPlan 字段一致
_DEMO_PLANS: list[dict[str, Any]] = [
    {
        "id": "demo-starter",
        "title": "体验档",
        "description": "本地演示：未接商户时仅展示流程与界面，不产生真实扣款。",
        "amount_cents": 990,
        "currency": "CNY",
        "badge": "演示",
    },
    {
        "id": "demo-standard",
        "title": "标准档",
        "description": "适合个人高频使用；接入支付宝后可替换为真实套餐与金额。",
        "amount_cents": 4990,
        "currency": "CNY",
        "badge": None,
    },
    {
        "id": "demo-pro",
        "title": "专业档",
        "description": "更高配额与优先响应；上线前请在环境变量中配置支付参数。",
        "amount_cents": 19900,
        "currency": "CNY",
        "badge": "推荐",
    },
]


def _integration_flags() -> dict[str, bool]:
    """支付宝：APPID + 应用私钥 + 支付宝公钥 + 已安装 SDK 时为已开通。"""
    return {
        "alipay_configured": mp_ali.alipay_ui_ready(),
        "market_sot": is_modstore_payment_sot(),
        "postgres_sot": is_fhd_postgres_payment_sot(),
        "backend": model_payment_backend(),
    }


def _plan_by_id(plan_id: str) -> dict[str, Any] | None:
    for p in _DEMO_PLANS:
        if p["id"] == plan_id:
            return p
    return None


@router.get("/plans")
def get_plans():
    return JSONResponse(
        {
            "success": True,
            "data": {
                "plans": list(_DEMO_PLANS),
                "integration": _integration_flags(),
            },
        }
    )


@router.get("/wechat-redirect")
def wechat_redirect(plan_id: str, market_user_id: int = 0):
    """FHD 宿主微信支付：重定向至修茈市场统一收银台。"""
    from app.infrastructure.payment.modstore_payment_proxy import wechat_checkout_redirect_url

    url = wechat_checkout_redirect_url(plan_id, market_user_id=market_user_id)
    if not url:
        return JSONResponse(
            {"success": False, "message": "请配置 XCAGI_MARKET_BASE_URL"},
            status_code=503,
        )
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=url, status_code=302)


@router.post("/checkout")
def checkout(
    body: dict[str, Any] = Body(default_factory=dict),
    user_agent: str | None = Header(default=None),
):
    if is_modstore_payment_sot():
        channel = str(body.get("channel") or "alipay").strip().lower()
        plan_id = str(body.get("plan_id") or "").strip()
        uid = int(body.get("market_user_id") or 0)
        proxied_err = None
        if plan_id:
            from app.infrastructure.payment.modstore_payment_proxy import proxy_checkout

            proxied = proxy_checkout(plan_id=plan_id, channel=channel, market_user_id=uid)
            if proxied.get("ok"):
                return JSONResponse({"success": True, "data": proxied.get("data")})
            proxied_err = proxied.get("error")
        return JSONResponse(
            {
                "success": False,
                "message": modstore_payment_hint(),
                "data": {
                    "use_checkout": "/api/market/payment/checkout",
                    "use_plans": "/api/market/payment/plans",
                    "proxy_error": proxied_err,
                },
            },
            status_code=409,
        )
    if is_json_legacy_payment_sot():
        import os

        dbu = (os.environ.get("DATABASE_URL") or "").strip().lower()
        if "postgresql" in dbu or "postgres://" in dbu:
            return JSONResponse(
                {
                    "success": False,
                    "message": (
                        "检测到 PostgreSQL DATABASE_URL，请将 MODEL_PAYMENT_BACKEND 设为 postgres；"
                        f"JSON 订单存储将于 {MODEL_PAYMENT_JSON_DEPRECATED_AFTER} 后废弃。"
                    ),
                    "data": {
                        "migrate_script": "scripts/migrate_fhd_json_orders_to_postgres.py",
                        "docs": "docs/guides/PAYMENT_SOT.md",
                    },
                },
                status_code=409,
            )
    plan_id = str(body.get("plan_id") or "").strip()
    legacy_channel = str(body.get("channel") or "").strip().lower()
    if legacy_channel and legacy_channel != "alipay":
        return JSONResponse(
            {"success": False, "message": "仅支持支付宝；请移除 channel 或传 channel=alipay"},
            status_code=400,
        )
    plan = _plan_by_id(plan_id)
    if not plan:
        return JSONResponse(
            {"success": False, "message": f"未知套餐: {plan_id}"},
            status_code=400,
        )

    order_id = f"mp-{uuid.uuid4().hex[:18]}"
    channel = "alipay"
    amount_yuan = f"{int(plan['amount_cents']) / 100:.2f}"
    subject = f"模型套餐-{plan['title']}"

    mp_ali.warn_notify_url_path_once()

    if not mp_ali.alipay_ui_ready():
        hint = (
            "当前为演示模式：未满足支付宝真实下单条件（需 ALIPAY_APP_ID、ALIPAY_APP_PRIVATE_KEY 或 "
            "ALIPAY_APP_PRIVATE_KEY_PATH、支付宝公钥（环境变量或默认 424/alipayPublicKey_RSA2.txt），"
            "并安装 python-alipay-sdk；沙箱请加 ALIPAY_DEBUG=1）。"
        )
        if mp_ali.credentials_ready() and mp_ali.sdk_import_error():
            hint = mp_ali.sdk_import_error() or hint
        logger.info(
            "[model-payment] demo checkout order_id=%s plan=%s (alipay not ready)",
            order_id,
            plan_id,
        )
        return JSONResponse(
            {
                "success": True,
                "data": {
                    "order_id": order_id,
                    "channel": channel,
                    "status": "demo_pending",
                    "amount_cents": plan["amount_cents"],
                    "plan_id": plan_id,
                    "client_payload": {"demo": True},
                    "redirect_url": None,
                    "qr_code": None,
                    "setup_hint": hint,
                },
            }
        )

    # 自动根据 User-Agent 选择 page.pay / wap.pay / 回退 precreate
    pay_res = mp_ali.create_pay_order(
        out_trade_no=order_id,
        subject=subject,
        total_amount=amount_yuan,
        user_agent=user_agent or "",
    )

    if not pay_res["ok"]:
        logger.warning(
            "[model-payment] pay_order failed order_id=%s message=%s raw=%s",
            order_id,
            pay_res.get("message"),
            pay_res.get("raw"),
        )
        return JSONResponse(
            {
                "success": False,
                "message": pay_res.get("message") or "支付宝下单失败",
            }
        )

    logger.info(
        "[model-payment] pay_order ok order_id=%s type=%s",
        order_id,
        pay_res.get("type"),
    )
    try:
        mp_orders.record_checkout_pending(
            out_trade_no=order_id,
            plan_id=plan_id,
            amount_cents=int(plan["amount_cents"]),
            amount_yuan=amount_yuan,
        )
    except OSError as e:
        logger.exception("[model-payment] 写入本地订单失败（notify 将无法幂等关联）: %s", e)

    return JSONResponse(
        {
            "success": True,
            "data": {
                "order_id": order_id,
                "channel": channel,
                "status": "pending_payment",
                "amount_cents": plan["amount_cents"],
                "plan_id": plan_id,
                "client_payload": pay_res.get("raw"),
                "redirect_url": pay_res.get("redirect_url"),
                "qr_code": pay_res.get("qr_code"),
            },
        }
    )


@router.post("/notify/alipay")
async def alipay_trade_notify(request: Request):
    """
    支付宝异步通知（需在开放平台配置 notify_url 指向本地址的公网 URL）。
    验签通过后返回纯文本 success；请勿在本接口中信任未验签参数做发货。
    """
    if not is_local_model_payment_sot():
        return PlainTextResponse("fail", status_code=410)
    try:
        form = await request.form()
    except Exception as e:
        logger.warning("alipay notify: bad form: %s", e)
        return PlainTextResponse("fail", status_code=400)

    data: dict[str, str] = {str(k): str(v) for k, v in form.items()}
    signature = data.pop("sign", None)
    if not signature:
        return PlainTextResponse("fail", status_code=400)

    if not mp_ali.credentials_ready():
        logger.error("alipay notify: credentials not configured")
        return PlainTextResponse("fail", status_code=503)

    try:
        ok = mp_ali.verify_notify(data, signature)
    except Exception as e:
        logger.exception("alipay notify verify error: %s", e)
        return PlainTextResponse("fail", status_code=500)

    if not ok:
        logger.warning("alipay notify: signature verification failed")
        return PlainTextResponse("fail", status_code=400)

    trade_status = data.get("trade_status", "")
    if trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED"):
        out_trade_no = str(data.get("out_trade_no") or "")
        trade_no = str(data.get("trade_no") or "")
        total_amount = str(data.get("total_amount") or "")
        reason, snap = mp_orders.apply_notify_paid(
            out_trade_no=out_trade_no,
            trade_no=trade_no,
            total_amount=total_amount,
        )
        if reason == "amount_mismatch":
            return PlainTextResponse("fail", status_code=400)
        if reason == "unknown_order":
            logger.warning(
                "[model-payment] notify: 无本地订单仍返回 success，避免支付宝无限重试 out_trade_no=%s",
                out_trade_no,
            )
        elif reason == "marked_paid" and snap:
            ent = snap.get("entitlement") if isinstance(snap, dict) else None
            logger.info(
                "[model-payment] 权益已发放 plan_id=%s amount_cents=%s purchase_count=%s",
                snap.get("plan_id"),
                snap.get("amount_cents"),
                (ent or {}).get("purchase_count") if isinstance(ent, dict) else None,
            )
    return PlainTextResponse("success")


@router.get("/diagnostics")
def diagnostics():
    """只读诊断：返回支付宝配置是否就绪、各字段来源、notify URL 是否对齐等，不含密钥内容。"""
    data = mp_ali.diagnostics_snapshot()
    backend = model_payment_backend()
    data["sot_backend"] = backend
    data["store_path"] = str(mp_orders.order_store_path())
    if is_fhd_postgres_payment_sot():
        data["db_table"] = "model_payment_orders"
        try:
            data["order_count"] = mp_orders.count_orders()
            data["json_migration_pending"] = mp_orders.json_store_has_unmigrated_orders()
        except Exception as exc:
            data["order_count_error"] = str(exc)[:200]
    return JSONResponse({"success": True, "data": data})


@router.get("/entitlements")
def entitlements():
    """已购权益列表（按 last_paid_at 倒序）。"""
    if is_modstore_payment_sot():
        return JSONResponse(
            {
                "success": False,
                "message": modstore_payment_hint(),
                "data": {"entitlements": []},
            },
            status_code=409,
        )
    items = mp_orders.list_entitlements()
    return JSONResponse(
        {"success": True, "data": {"entitlements": items, "backend": model_payment_backend()}}
    )


@router.get("/query/{out_trade_no}")
def query_trade(out_trade_no: str):
    """alipay.trade.query：查询交易状态。同时返回本地订单快照。"""
    res = mp_ali.query_order(out_trade_no=out_trade_no)
    local = mp_orders.get_order(out_trade_no)
    if not res["ok"]:
        return JSONResponse(
            {
                "success": False,
                "message": res.get("message") or "查询失败",
                "data": {"local": local},
            }
        )
    return JSONResponse(
        {
            "success": True,
            "data": {
                "trade": res.get("raw"),
                "local": local,
            },
        }
    )


@router.post("/refund")
def refund_trade(body: dict[str, Any] = Body(default_factory=dict)):
    """alipay.trade.refund：发起退款。body: out_trade_no, refund_amount, out_request_no?, refund_reason?"""
    out_trade_no = str(body.get("out_trade_no") or "").strip()
    refund_amount = str(body.get("refund_amount") or "").strip()
    out_request_no = str(body.get("out_request_no") or "").strip() or None
    refund_reason = str(body.get("refund_reason") or "").strip() or None

    if not out_trade_no:
        return JSONResponse({"success": False, "message": "out_trade_no 必填"}, status_code=400)
    if not refund_amount:
        return JSONResponse(
            {"success": False, "message": "refund_amount 必填（元）"}, status_code=400
        )

    res = mp_ali.refund_order(
        out_trade_no=out_trade_no,
        refund_amount=refund_amount,
        out_request_no=out_request_no,
        refund_reason=refund_reason,
    )
    if not res["ok"]:
        logger.warning(
            "[model-payment] refund failed out_trade_no=%s message=%s",
            out_trade_no,
            res.get("message"),
        )
        return JSONResponse({"success": False, "message": res.get("message") or "退款失败"})

    try:
        mp_orders.update_order_status(
            out_trade_no=out_trade_no,
            status="refunded",
            extra={
                "refund_amount": refund_amount,
                "refund_request_no": out_request_no or out_trade_no,
                "refund_reason": refund_reason,
            },
        )
    except OSError as e:
        logger.exception("[model-payment] 写入退款本地记录失败: %s", e)

    logger.info("[model-payment] refund ok out_trade_no=%s amount=%s", out_trade_no, refund_amount)
    return JSONResponse({"success": True, "data": res.get("raw")})


@router.post("/close")
def close_trade(body: dict[str, Any] = Body(default_factory=dict)):
    """alipay.trade.close：关闭未付款交易。body: out_trade_no 或 trade_no。"""
    out_trade_no = str(body.get("out_trade_no") or "").strip() or None
    trade_no = str(body.get("trade_no") or "").strip() or None
    if not out_trade_no and not trade_no:
        return JSONResponse(
            {"success": False, "message": "out_trade_no 与 trade_no 至少提供一个"},
            status_code=400,
        )

    res = mp_ali.close_order(out_trade_no=out_trade_no, trade_no=trade_no)
    if not res["ok"]:
        return JSONResponse({"success": False, "message": res.get("message") or "关闭交易失败"})

    if out_trade_no:
        try:
            mp_orders.update_order_status(out_trade_no=out_trade_no, status="closed")
        except OSError as e:
            logger.exception("[model-payment] 写入关闭本地记录失败: %s", e)

    logger.info("[model-payment] close ok out_trade_no=%s trade_no=%s", out_trade_no, trade_no)
    return JSONResponse({"success": True, "data": res.get("raw")})


@router.get("/refund/query")
def refund_query(out_trade_no: str, out_request_no: str | None = None):
    """alipay.trade.fastpay.refund.query：退款查询。不传 out_request_no 则默认等于 out_trade_no。"""
    if not out_trade_no:
        return JSONResponse({"success": False, "message": "out_trade_no 必填"}, status_code=400)
    res = mp_ali.query_refund(out_trade_no=out_trade_no, out_request_no=out_request_no)
    if not res["ok"]:
        return JSONResponse({"success": False, "message": res.get("message") or "退款查询失败"})
    return JSONResponse({"success": True, "data": res.get("raw")})
