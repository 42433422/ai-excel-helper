"""模型支付：支付宝公钥模式 + 订单码预下单（alipay.trade.precreate）。"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

# 兜底加载 .env（如果尚未加载）
try:
    from dotenv import load_dotenv

    _repo_root = Path(__file__).resolve().parents[3]
    for _env_file in (_repo_root / ".env", _repo_root / "XCAGI" / ".env"):
        if _env_file.is_file():
            load_dotenv(_env_file, override=False)
except Exception:
    pass

logger = logging.getLogger(__name__)


def _env(name: str) -> str:
    return (os.environ.get(name) or "").strip()


def _pem_from_env(name: str) -> str:
    raw = _env(name)
    if not raw:
        return ""
    return raw.replace("\\n", "\n")


def _read_file_from_env(path_var: str) -> str:
    path = _env(path_var)
    if not path:
        return ""
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        logger.warning("无法读取 %s=%s", path_var, path)
        return ""


def _repo_root() -> Path:
    """仓库根目录(…/FHD)。此文件位于 ``app/infrastructure/payment``,上溯 3 级抵达根。"""
    return Path(__file__).resolve().parents[3]


def _default_bundled_alipay_public_key() -> str:
    """未设置环境变量时，读取 ``424/alipayPublicKey_RSA2.txt``（标准 PEM）。"""
    p = _repo_root() / "424" / "alipayPublicKey_RSA2.txt"
    if not p.is_file():
        return ""
    try:
        return p.read_text(encoding="utf-8").strip()
    except OSError:
        logger.warning("无法读取默认支付宝公钥文件: %s", p)
        return ""


def alipay_app_id() -> str:
    return _env("ALIPAY_APP_ID") or _env("ALIPAY_PID")


def app_private_key_pem() -> str:
    pem = _pem_from_env("ALIPAY_APP_PRIVATE_KEY")
    if pem:
        return pem
    return _read_file_from_env("ALIPAY_APP_PRIVATE_KEY_PATH")


def alipay_public_key_pem() -> str:
    """开放平台「支付宝公钥」文本（验签异步通知 / 同步响应），不是你的应用公钥。

    优先级：``ALIPAY_ALIPAY_PUBLIC_KEY`` → ``ALIPAY_ALIPAY_PUBLIC_KEY_PATH`` →
    仓库内 ``424/alipayPublicKey_RSA2.txt``。
    """
    pem = _pem_from_env("ALIPAY_ALIPAY_PUBLIC_KEY")
    if pem:
        return pem
    path_pem = _read_file_from_env("ALIPAY_ALIPAY_PUBLIC_KEY_PATH")
    if path_pem:
        return path_pem
    return _default_bundled_alipay_public_key()


def alipay_debug() -> bool:
    return _env("ALIPAY_DEBUG").lower() in ("1", "true", "yes")


def notify_url_default() -> str | None:
    u = _env("ALIPAY_NOTIFY_URL")
    return u or None


_warned_notify_url = False


def warn_notify_url_path_once() -> None:
    """若配置了 ``ALIPAY_NOTIFY_URL``，校验 path 是否为 ``/api/model-payment/notify/alipay``。"""
    global _warned_notify_url
    if _warned_notify_url:
        return
    _warned_notify_url = True
    u = notify_url_default()
    if not u:
        return
    from urllib.parse import urlparse

    path = (urlparse(u).path or "").rstrip("/")
    expected = "/api/model-payment/notify/alipay"
    if path != expected:
        logger.warning(
            "ALIPAY_NOTIFY_URL 的 path 应为「%s」，当前为「%s」。"
            " 开放平台异步通知地址须与本服务路由一致，否则收不到回调。",
            expected,
            urlparse(u).path or "/",
        )


def sdk_import_error() -> str | None:
    try:
        from alipay import AliPay  # noqa: F401
    except ImportError:
        return "未安装 python-alipay-sdk，请在运行环境执行: pip install python-alipay-sdk"
    return None


def credentials_ready() -> bool:
    return bool(alipay_app_id() and app_private_key_pem() and alipay_public_key_pem())


def alipay_ui_ready() -> bool:
    """前端「已开通」与真实预下单共用同一套判断。"""
    return credentials_ready() and sdk_import_error() is None


def build_client():
    """构造 AliPay 客户端；缺依赖或配置时抛 RuntimeError。"""
    missing_sdk = sdk_import_error()
    if missing_sdk:
        raise RuntimeError(missing_sdk)
    if not credentials_ready():
        raise RuntimeError(
            "支付宝配置不完整：需要 ALIPAY_APP_ID、ALIPAY_APP_PRIVATE_KEY（或 ALIPAY_APP_PRIVATE_KEY_PATH）、"
            "以及 ALIPAY_ALIPAY_PUBLIC_KEY / ALIPAY_ALIPAY_PUBLIC_KEY_PATH，或仓库内 424/alipayPublicKey_RSA2.txt"
        )
    from alipay import AliPay

    return AliPay(
        appid=alipay_app_id(),
        app_notify_url=notify_url_default(),
        app_private_key_string=app_private_key_pem(),
        alipay_public_key_string=alipay_public_key_pem(),
        sign_type="RSA2",
        debug=alipay_debug(),
    )


def _build_common_kwargs(
    *,
    out_trade_no: str,
    subject: str,
    total_amount: str,
    notify_url: str | None = None,
) -> dict[str, Any]:
    """构造订单公共参数。"""
    kwargs: dict[str, Any] = {
        "out_trade_no": out_trade_no,
        "total_amount": total_amount,
        "subject": subject[:256],
    }
    nu = notify_url or notify_url_default()
    if nu:
        kwargs["notify_url"] = nu
    return kwargs


def _try_precreate(
    *,
    out_trade_no: str,
    subject: str,
    total_amount: str,
    notify_url: str | None = None,
) -> dict[str, Any]:
    """尝试 alipay.trade.precreate（订单码/当面付），返回标准格式。"""
    if not credentials_ready():
        return {
            "ok": False,
            "qr_code": None,
            "message": (
                "支付宝密钥未配全：需要 ALIPAY_APP_ID、ALIPAY_APP_PRIVATE_KEY（或 _PATH）、"
                "以及 ALIPAY_ALIPAY_PUBLIC_KEY / _PATH 或 424/alipayPublicKey_RSA2.txt"
            ),
            "raw": None,
        }
    try:
        client = build_client()
    except RuntimeError as e:
        return {"ok": False, "qr_code": None, "message": str(e), "raw": None}

    kwargs = _build_common_kwargs(
        out_trade_no=out_trade_no,
        subject=subject,
        total_amount=total_amount,
        notify_url=notify_url,
    )

    try:
        result = client.api_alipay_trade_precreate(**kwargs)
    except Exception as e:
        logger.exception("alipay.trade.precreate 请求异常")
        return {"ok": False, "qr_code": None, "message": f"请求支付宝异常: {e}", "raw": None}

    if not isinstance(result, dict):
        return {"ok": False, "qr_code": None, "message": "支付宝返回格式异常", "raw": None}

    if result.get("code") == "10000" and result.get("qr_code"):
        return {"ok": True, "qr_code": str(result["qr_code"]), "message": None, "raw": result}

    msg = result.get("sub_msg") or result.get("msg") or "预下单失败"
    return {"ok": False, "qr_code": None, "message": str(msg), "raw": result}


def precreate_order(
    *,
    out_trade_no: str,
    subject: str,
    total_amount: str,
    notify_url: str | None = None,
) -> dict[str, Any]:
    """
    调用 alipay.trade.precreate。
    返回: {"ok": bool, "qr_code": str | None, "message": str | None, "raw": dict | None}
    """
    return _try_precreate(
        out_trade_no=out_trade_no,
        subject=subject,
        total_amount=total_amount,
        notify_url=notify_url,
    )


def _try_page_pay(
    *,
    out_trade_no: str,
    subject: str,
    total_amount: str,
    return_url: str | None = None,
    notify_url: str | None = None,
) -> dict[str, Any]:
    """
    电脑网站支付 alipay.trade.page.pay。
    返回: {"ok": bool, "order_string": str | None, "gateway": str, "message": str | None, "raw": dict | None}
    """
    if not credentials_ready():
        return {
            "ok": False,
            "order_string": None,
            "gateway": "",
            "message": "支付宝密钥未配全",
            "raw": None,
        }
    try:
        client = build_client()
    except RuntimeError as e:
        return {"ok": False, "order_string": None, "gateway": "", "message": str(e), "raw": None}

    kwargs = _build_common_kwargs(
        out_trade_no=out_trade_no,
        subject=subject,
        total_amount=total_amount,
        notify_url=notify_url,
    )
    if return_url:
        kwargs["return_url"] = return_url

    try:
        # python-alipay-sdk 3.x 的 page_pay 返回可直接拼在网关后的 order_string
        order_string = client.api_alipay_trade_page_pay(**kwargs)
    except Exception as e:
        logger.exception("alipay.trade.page.pay 请求异常")
        return {
            "ok": False,
            "order_string": None,
            "gateway": "",
            "message": f"请求支付宝异常: {e}",
            "raw": None,
        }

    gateway = "https://openapi.alipay.com/gateway.do"
    if alipay_debug():
        gateway = "https://openapi-sandbox.dl.alipaydev.com/gateway.do"

    return {
        "ok": True,
        "order_string": order_string,
        "gateway": gateway,
        "message": None,
        "raw": {"order_string": order_string},
    }


def _try_wap_pay(
    *,
    out_trade_no: str,
    subject: str,
    total_amount: str,
    quit_url: str | None = None,
    return_url: str | None = None,
    notify_url: str | None = None,
) -> dict[str, Any]:
    """
    手机网站支付 alipay.trade.wap.pay。
    返回: {"ok": bool, "order_string": str | None, "gateway": str, "message": str | None, "raw": dict | None}
    """
    if not credentials_ready():
        return {
            "ok": False,
            "order_string": None,
            "gateway": "",
            "message": "支付宝密钥未配全",
            "raw": None,
        }
    try:
        client = build_client()
    except RuntimeError as e:
        return {"ok": False, "order_string": None, "gateway": "", "message": str(e), "raw": None}

    kwargs = _build_common_kwargs(
        out_trade_no=out_trade_no,
        subject=subject,
        total_amount=total_amount,
        notify_url=notify_url,
    )
    # wap.pay 额外参数
    if quit_url:
        kwargs["quit_url"] = quit_url
    if return_url:
        kwargs["return_url"] = return_url

    try:
        order_string = client.api_alipay_trade_wap_pay(**kwargs)
    except Exception as e:
        logger.exception("alipay.trade.wap.pay 请求异常")
        return {
            "ok": False,
            "order_string": None,
            "gateway": "",
            "message": f"请求支付宝异常: {e}",
            "raw": None,
        }

    gateway = "https://openapi.alipay.com/gateway.do"
    if alipay_debug():
        gateway = "https://openapi-sandbox.dl.alipaydev.com/gateway.do"

    return {
        "ok": True,
        "order_string": order_string,
        "gateway": gateway,
        "message": None,
        "raw": {"order_string": order_string},
    }


def create_pay_order(
    *,
    out_trade_no: str,
    subject: str,
    total_amount: str,
    user_agent: str = "",
    return_url: str | None = None,
    quit_url: str | None = None,
    notify_url: str | None = None,
) -> dict[str, Any]:
    """
    根据 User-Agent 自动选择支付方式：
    - 含 Mobile|Android|iPhone|iPad 等 → wap.pay（手机网站支付）
    - 否则 → page.pay（电脑网站支付）
    - 若两者都失败，回退尝试 precreate（订单码）

    返回统一格式：
    {
        "ok": bool,
        "type": "page" | "wap" | "precreate" | "",
        "redirect_url": str | None,  # 可直接跳转的完整 URL
        "qr_code": str | None,       # precreate 模式专用
        "message": str | None,
        "raw": dict | None,
    }
    """
    ua = (user_agent or "").lower()
    is_mobile = any(
        k in ua for k in ("mobile", "android", "iphone", "ipad", "ipod", "windows phone")
    )

    # 先尝试网站支付（page 或 wap）
    if is_mobile:
        logger.info("[alipay] 检测到移动端 UA，使用 wap.pay: %s...", ua[:60])
        res = _try_wap_pay(
            out_trade_no=out_trade_no,
            subject=subject,
            total_amount=total_amount,
            quit_url=quit_url,
            return_url=return_url,
            notify_url=notify_url,
        )
        if res["ok"]:
            gateway = res.get("gateway", "")
            order_string = res.get("order_string", "")
            redirect_url = f"{gateway}?{order_string}" if gateway and order_string else None
            return {
                "ok": True,
                "type": "wap",
                "redirect_url": redirect_url,
                "qr_code": None,
                "message": None,
                "raw": res.get("raw"),
            }
        # wap 失败（如权限不足）降级到 page
        logger.warning("[alipay] wap.pay 失败，尝试 page.pay: %s", res.get("message"))

    # PC 端或 wap 失败 → 尝试 page.pay
    res = _try_page_pay(
        out_trade_no=out_trade_no,
        subject=subject,
        total_amount=total_amount,
        return_url=return_url,
        notify_url=notify_url,
    )
    if res["ok"]:
        gateway = res.get("gateway", "")
        order_string = res.get("order_string", "")
        redirect_url = f"{gateway}?{order_string}" if gateway and order_string else None
        return {
            "ok": True,
            "type": "page",
            "redirect_url": redirect_url,
            "qr_code": None,
            "message": None,
            "raw": res.get("raw"),
        }

    # page 也失败（权限不足等），最后回退尝试 precreate（订单码）
    logger.warning("[alipay] page.pay 失败，回退尝试 precreate: %s", res.get("message"))
    pr = _try_precreate(
        out_trade_no=out_trade_no,
        subject=subject,
        total_amount=total_amount,
        notify_url=notify_url,
    )
    if pr["ok"]:
        return {
            "ok": True,
            "type": "precreate",
            "redirect_url": None,
            "qr_code": pr.get("qr_code"),
            "message": None,
            "raw": pr.get("raw"),
        }

    # 全失败
    return {
        "ok": False,
        "type": "",
        "redirect_url": None,
        "qr_code": None,
        "message": res.get("message") or pr.get("message") or "支付下单失败",
        "raw": res.get("raw") or pr.get("raw"),
    }


def verify_notify(data: dict[str, str], signature: str) -> bool:
    """验签支付宝异步通知（调用方需已 pop 掉 sign）。"""
    client = build_client()
    return bool(client.verify(data, signature))


def _standard_api_result(
    result: Any,
    default_error: str,
) -> dict[str, Any]:
    """把支付宝 OpenAPI 返回统一成 {ok, message, raw}。"""
    if not isinstance(result, dict):
        return {"ok": False, "message": "支付宝返回格式异常", "raw": None}
    if result.get("code") == "10000":
        return {"ok": True, "message": None, "raw": result}
    msg = result.get("sub_msg") or result.get("msg") or default_error
    return {"ok": False, "message": str(msg), "raw": result}


def query_order(*, out_trade_no: str | None = None, trade_no: str | None = None) -> dict[str, Any]:
    """alipay.trade.query：查询交易状态。out_trade_no / trade_no 至少一个。"""
    if not out_trade_no and not trade_no:
        return {"ok": False, "message": "out_trade_no 与 trade_no 至少提供一个", "raw": None}
    try:
        client = build_client()
    except RuntimeError as e:
        return {"ok": False, "message": str(e), "raw": None}
    try:
        kwargs: dict[str, Any] = {}
        if out_trade_no:
            kwargs["out_trade_no"] = out_trade_no
        if trade_no:
            kwargs["trade_no"] = trade_no
        result = client.api_alipay_trade_query(**kwargs)
    except Exception as e:
        logger.exception("alipay.trade.query 请求异常")
        return {"ok": False, "message": f"请求支付宝异常: {e}", "raw": None}
    return _standard_api_result(result, "交易查询失败")


def refund_order(
    *,
    out_trade_no: str | None = None,
    trade_no: str | None = None,
    refund_amount: str,
    out_request_no: str | None = None,
    refund_reason: str | None = None,
) -> dict[str, Any]:
    """
    alipay.trade.refund：统一收单交易退款。
    - out_trade_no 与 trade_no 至少一个。
    - out_request_no 未传则默认等于 out_trade_no（即全额退款时只退一次）。
    """
    if not out_trade_no and not trade_no:
        return {"ok": False, "message": "out_trade_no 与 trade_no 至少提供一个", "raw": None}
    try:
        client = build_client()
    except RuntimeError as e:
        return {"ok": False, "message": str(e), "raw": None}
    try:
        kwargs: dict[str, Any] = {"refund_amount": refund_amount}
        if out_trade_no:
            kwargs["out_trade_no"] = out_trade_no
        if trade_no:
            kwargs["trade_no"] = trade_no
        if out_request_no:
            kwargs["out_request_no"] = out_request_no
        if refund_reason:
            kwargs["refund_reason"] = refund_reason
        result = client.api_alipay_trade_refund(**kwargs)
    except Exception as e:
        logger.exception("alipay.trade.refund 请求异常")
        return {"ok": False, "message": f"请求支付宝异常: {e}", "raw": None}
    return _standard_api_result(result, "退款失败")


def close_order(*, out_trade_no: str | None = None, trade_no: str | None = None) -> dict[str, Any]:
    """alipay.trade.close：关闭未付款交易。out_trade_no 与 trade_no 至少一个。"""
    if not out_trade_no and not trade_no:
        return {"ok": False, "message": "out_trade_no 与 trade_no 至少提供一个", "raw": None}
    try:
        client = build_client()
    except RuntimeError as e:
        return {"ok": False, "message": str(e), "raw": None}
    try:
        kwargs: dict[str, Any] = {}
        if out_trade_no:
            kwargs["out_trade_no"] = out_trade_no
        if trade_no:
            kwargs["trade_no"] = trade_no
        result = client.api_alipay_trade_close(**kwargs)
    except Exception as e:
        logger.exception("alipay.trade.close 请求异常")
        return {"ok": False, "message": f"请求支付宝异常: {e}", "raw": None}
    return _standard_api_result(result, "关闭交易失败")


def query_refund(*, out_trade_no: str, out_request_no: str | None = None) -> dict[str, Any]:
    """alipay.trade.fastpay.refund.query：退款查询。out_request_no 默认等于 out_trade_no。"""
    if not out_trade_no:
        return {"ok": False, "message": "out_trade_no 必填", "raw": None}
    try:
        client = build_client()
    except RuntimeError as e:
        return {"ok": False, "message": str(e), "raw": None}
    req_no = out_request_no or out_trade_no
    try:
        # SDK 3.x：第一个位置参数为 out_request_no，关键字 out_trade_no
        result = client.api_alipay_trade_fastpay_refund_query(req_no, out_trade_no=out_trade_no)
    except Exception as e:
        logger.exception("alipay.trade.fastpay.refund.query 请求异常")
        return {"ok": False, "message": f"请求支付宝异常: {e}", "raw": None}
    return _standard_api_result(result, "退款查询失败")


def _private_key_source() -> str:
    """返回私钥来源描述：env / path / missing。"""
    if _pem_from_env("ALIPAY_APP_PRIVATE_KEY"):
        return "env"
    if _env("ALIPAY_APP_PRIVATE_KEY_PATH") and _read_file_from_env("ALIPAY_APP_PRIVATE_KEY_PATH"):
        return "path"
    return "missing"


def _public_key_source() -> str:
    """返回支付宝公钥来源描述：env / path / bundled / missing。"""
    if _pem_from_env("ALIPAY_ALIPAY_PUBLIC_KEY"):
        return "env"
    if _env("ALIPAY_ALIPAY_PUBLIC_KEY_PATH") and _read_file_from_env(
        "ALIPAY_ALIPAY_PUBLIC_KEY_PATH"
    ):
        return "path"
    if _default_bundled_alipay_public_key():
        return "bundled"
    return "missing"


def _notify_url_path_ok(url: str | None) -> bool:
    if not url:
        return False
    from urllib.parse import urlparse

    path = (urlparse(url).path or "").rstrip("/")
    return path == "/api/model-payment/notify/alipay"


def diagnostics_snapshot() -> dict[str, Any]:
    """只读诊断信息：不包含任何密钥内容，仅返回「是否已配置/来源」。"""
    sdk_err = sdk_import_error()
    notify_url = notify_url_default()
    return {
        "alipay_configured": alipay_ui_ready(),
        "sdk_installed": sdk_err is None,
        "sdk_import_error": sdk_err,
        "app_id_set": bool(alipay_app_id()),
        "private_key_source": _private_key_source(),
        "public_key_source": _public_key_source(),
        "notify_url": notify_url,
        "notify_url_path_ok": _notify_url_path_ok(notify_url),
        "notify_url_path_expected": "/api/model-payment/notify/alipay",
        "debug_mode": alipay_debug(),
    }
