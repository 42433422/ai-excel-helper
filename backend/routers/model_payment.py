"""个人模型 / API 额度：套餐列表与下单占位接口（支付调起与回调需自行接入）。

扫码（二维码）对接要点（PC 网页常见形态）：
- 微信：WeChat Pay API v3 的 Native 下单 ``POST .../v3/pay/transactions/native``，
  成功响应里的 ``code_url`` 即为「可被微信扫一扫识别」的链接；后端原样返回给前端，
  前端用 QR 库把字符串画成二维码图片即可。
- 支付宝：``alipay.trade.precreate``（当面付预下单），响应里的 ``qr_code`` 同理交给前端画码。
- 手机浏览器里更常见 JSAPI / WAP 调起客户端，不一定走二维码；与本页「展示码」是不同产品形态。
回调：微信 ``/v3/pay/transactions/out-trade-no/{out_trade_no}`` 查单或支付结果通知；
支付宝异步 ``notify_url`` 验签后改本地订单状态。
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

try:
    from alipay import AliPay
    from alipay.utils import AliPayConfig
    ALIPAY_SDK_AVAILABLE = True
except ImportError:
    ALIPAY_SDK_AVAILABLE = False

router = APIRouter(prefix="/api/model-payment", tags=["model_payment"])

_alipay_instance: AliPay | None = None


def _get_alipay() -> AliPay | None:
    global _alipay_instance
    if not ALIPAY_SDK_AVAILABLE:
        return None
    if _alipay_instance is not None:
        return _alipay_instance

    app_id = os.environ.get("ALIPAY_APP_ID", "").strip()
    app_private_key = os.environ.get("ALIPAY_APP_PRIVATE_KEY", "").strip()
    app_private_key_path = os.environ.get("ALIPAY_APP_PRIVATE_KEY_PATH", "").strip()
    alipay_public_key = os.environ.get("ALIPAY_PUBLIC_KEY", "").strip()
    alipay_public_key_path = os.environ.get("ALIPAY_PUBLIC_KEY_PATH", "").strip()
    notify_url = os.environ.get("ALIPAY_NOTIFY_URL", "").strip()

    if not app_id:
        return None

    if app_private_key_path and not app_private_key:
        with open(app_private_key_path, "r", encoding="utf-8") as f:
            app_private_key = f.read()

    if alipay_public_key_path and not alipay_public_key:
        with open(alipay_public_key_path, "r", encoding="utf-8") as f:
            alipay_public_key = f.read()

    if not app_private_key or not alipay_public_key:
        return None

    config = AliPayConfig(
        app_id=app_id,
        app_notify_url=notify_url or None,
        app_private_key=app_private_key,
        alipay_public_key=alipay_public_key,
        sign_type="RSA2",
    )
    _alipay_instance = AliPay(config=config)
    return _alipay_instance


def _checkout_data(
    order_id: str,
    plan: dict[str, Any],
    channel: str,
    status: str,
    *,
    client_payload: Any = None,
    setup_hint: str | None = None,
    code_url: str | None = None,
    qr_code: str | None = None,
) -> dict[str, Any]:
    """统一字段：接入真实 SDK 后把 ``code_url``（微信 Native）或 ``qr_code``（支付宝 precreate）填上。"""
    d: dict[str, Any] = {
        "order_id": order_id,
        "channel": channel,
        "status": status,
        "amount_cents": plan["amount_cents"],
        "plan_id": plan["id"],
        "client_payload": client_payload,
        "code_url": code_url,
        "qr_code": qr_code,
    }
    if setup_hint:
        d["setup_hint"] = setup_hint
    return d

_PLANS: list[dict[str, Any]] = [
    {
        "id": "api-lite",
        "title": "个人 · 轻量",
        "description": "适合日常少量对话或试用，先买一小档用着看。",
        "amount_cents": 9900,
        "currency": "CNY",
        "badge": "推荐",
    },
    {
        "id": "api-team",
        "title": "个人 · 畅享",
        "description": "用量稍大、想少充几次时的个人档位，可按需改价与说明。",
        "amount_cents": 49900,
        "currency": "CNY",
        "badge": None,
    },
    {
        "id": "api-bundle",
        "title": "个人 · 组合",
        "description": "折中价位的一档，适合个人长期轻度使用。",
        "amount_cents": 19900,
        "currency": "CNY",
        "badge": None,
    },
]


def _wechat_configured() -> bool:
    return bool(os.environ.get("WECHAT_PAY_MCH_ID", "").strip() and os.environ.get("WECHAT_PAY_API_V3_KEY", "").strip())


def _alipay_configured() -> bool:
    return _get_alipay() is not None


class CheckoutBody(BaseModel):
    plan_id: str = Field(..., min_length=1)
    channel: Literal["wechat", "alipay"]


@router.get("/plans")
async def list_plans() -> dict[str, Any]:
    return {
        "success": True,
        "data": {
            "plans": _PLANS,
            "integration": {
                "wechat_configured": _wechat_configured(),
                "alipay_configured": _alipay_configured(),
            },
        },
    }


@router.post("/checkout")
async def create_checkout(body: CheckoutBody) -> dict[str, Any]:
    plan = next((p for p in _PLANS if p["id"] == body.plan_id), None)
    if not plan:
        return {"success": False, "message": f"未知套餐: {body.plan_id}"}

    order_id = str(uuid.uuid4())
    wx_ok = _wechat_configured()
    ali_ok = _alipay_configured()

    # 尚未接官方 SDK 时统一返回占位说明；接入后在此分支返回 prepay_id / orderStr 等
    if body.channel == "wechat" and not wx_ok:
        return {
            "success": True,
            "data": _checkout_data(
                order_id,
                plan,
                "wechat",
                "pending_provider_config",
                setup_hint="个人环境未检测到微信商户变量；当前为占位订单。",
            ),
        }

    if body.channel == "alipay" and not ali_ok:
        return {
            "success": True,
            "data": _checkout_data(
                order_id,
                plan,
                "alipay",
                "pending_provider_config",
                setup_hint="个人环境未检测到支付宝应用变量；当前为占位订单。",
            ),
        }

    if body.channel == "wechat" and wx_ok:
        return {
            "success": True,
            "data": _checkout_data(
                order_id,
                plan,
                "wechat",
                "stub_ready",
                setup_hint=(
                    "已检测到微信侧关键变量；扫码请接 Native 下单，把返回的 code_url 填入本接口的 "
                    "data.code_url（勿与 JSAPI 的调起参数混淆）。"
                ),
            ),
        }

    if body.channel == "alipay" and ali_ok:
        alipay = _get_alipay()
        if alipay:
            try:
                subject = f"FHD API 套餐充值 - {plan['title']}"
                total_amount = str(plan["amount_cents"] / 100.0)
                out_trade_no = order_id

                response = alipay.alipay_trade_precreate(
                    out_trade_no=out_trade_no,
                    total_amount=total_amount,
                    subject=subject,
                    timeout_express="15m",
                )
                qr_code = response.get("qr_code", "")
                return {
                    "success": True,
                    "data": _checkout_data(
                        order_id,
                        plan,
                        "alipay",
                        "await_scan",
                        code_url=qr_code,
                        qr_code=qr_code,
                    ),
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"支付宝预下单失败: {str(e)}",
                }

    return {
        "success": True,
        "data": _checkout_data(
            order_id,
            plan,
            "alipay",
            "stub_ready",
            setup_hint=(
                "已检测到支付宝侧关键变量；扫码请接 alipay.trade.precreate，把返回的 qr_code 填入 "
                "data.qr_code。"
            ),
        ),
    }


class AlipayNotifyBody(BaseModel):
    out_trade_no: str
    trade_status: str
    trade_no: str


@router.post("/alipay/notify")
async def alipay_notify(body: dict[str, Any]):
    alipay = _get_alipay()
    if not alipay:
        return {"success": False, "message": "支付宝未配置"}

    try:
        signature = body.pop("sign", None)
        verified = alipay.verify(body, signature)
        if not verified:
            return {"success": False, "message": "验签失败"}

        out_trade_no = body.get("out_trade_no", "")
        trade_status = body.get("trade_status", "")

        if trade_status in ("TRADE_SUCCESS", "TRADE_FINISHED"):
            return {
                "success": True,
                "data": {
                    "order_id": out_trade_no,
                    "status": "paid",
                    "trade_status": trade_status,
                },
            }
        return {"success": True, "message": "收到通知"}
    except Exception as e:
        return {"success": False, "message": str(e)}
