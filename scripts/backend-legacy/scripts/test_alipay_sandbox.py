"""
支付宝沙箱自测脚本。

- 读取仓库根 ``.env`` 与 ``XCAGI/.env`` 后，打印诊断摘要（不含密钥）。
- 可选 ``--precreate`` 发起 ``alipay.trade.precreate`` 测试下单（订单码）。
- 可选 ``--pagepay`` 发起 ``alipay.trade.page.pay`` 测试下单（电脑网站支付）。
- 可选 ``--wappay`` 发起 ``alipay.trade.wap.pay`` 测试下单（手机网站支付）。
- 可选 ``--pay`` 使用 ``create_pay_order`` 自动根据 UA 选择支付方式。
- 可选 ``--verify-notify <file>`` 读取一份 form-urlencoded 文本离线验签。

上述测试下单**不会**写入 ``data/model_payment_orders.json``。

用法：

    python -m backend.scripts.test_alipay_sandbox
    python -m backend.scripts.test_alipay_sandbox --pagepay
    python -m backend.scripts.test_alipay_sandbox --wappay
    python -m backend.scripts.test_alipay_sandbox --verify-notify path/to/notify.txt

form 文本示例（一行，见支付宝文档）：

    app_id=...&out_trade_no=...&trade_status=TRADE_SUCCESS&sign=xxx&...
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import uuid
from pathlib import Path
from urllib.parse import parse_qsl


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_dotenvs() -> list[str]:
    """顺序加载 <repo>/.env 和 <repo>/XCAGI/.env，返回已加载路径列表。"""
    loaded: list[str] = []
    try:
        from dotenv import load_dotenv
    except ImportError:
        return loaded
    for candidate in (_repo_root() / ".env", _repo_root() / "XCAGI" / ".env"):
        if candidate.is_file():
            load_dotenv(candidate, override=False)
            loaded.append(str(candidate))
    return loaded


def _ensure_repo_on_path() -> None:
    root = str(_repo_root())
    if root not in sys.path:
        sys.path.insert(0, root)


def _print_header(title: str) -> None:
    print(f"\n=== {title} ===")


def _print_diagnostics() -> None:
    from app.infrastructure.payment import alipay as mp_ali
    from app.infrastructure.payment import order_store as mp_orders

    snap = mp_ali.diagnostics_snapshot()
    snap["store_path"] = str(mp_orders.order_store_path())
    _print_header("Diagnostics")
    print(json.dumps(snap, ensure_ascii=False, indent=2))


def _do_precreate(amount: str, subject: str) -> int:
    from app.infrastructure.payment import alipay as mp_ali

    if not mp_ali.credentials_ready():
        print("[precreate] 跳过：支付宝密钥未配全，请先设置环境变量。", file=sys.stderr)
        return 2
    if mp_ali.sdk_import_error():
        print(f"[precreate] 跳过：{mp_ali.sdk_import_error()}", file=sys.stderr)
        return 2

    out_trade_no = f"SANDBOX-{uuid.uuid4().hex[:18]}"
    _print_header("Precreate")
    print(f"out_trade_no = {out_trade_no}")
    print(f"total_amount = {amount}")
    print(f"subject      = {subject}")
    print(f"debug(sandbox)= {mp_ali.alipay_debug()}")

    res = mp_ali.precreate_order(
        out_trade_no=out_trade_no,
        total_amount=amount,
        subject=subject,
    )
    raw = res.get("raw")
    summary = {
        "ok": res.get("ok"),
        "qr_code": res.get("qr_code"),
        "message": res.get("message"),
        "code": (raw or {}).get("code") if isinstance(raw, dict) else None,
        "msg": (raw or {}).get("msg") if isinstance(raw, dict) else None,
        "sub_code": (raw or {}).get("sub_code") if isinstance(raw, dict) else None,
        "sub_msg": (raw or {}).get("sub_msg") if isinstance(raw, dict) else None,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if res.get("ok"):
        print("\n扫描上方 qr_code 对应的二维码即可完成沙箱付款。")
        print("（该订单号仅用于自测，未写入本地订单文件，无法触发本系统的 notify 幂等逻辑。）")
        return 0
    return 1


def _do_verify_notify(path: Path) -> int:
    from app.infrastructure.payment import alipay as mp_ali

    if not mp_ali.credentials_ready():
        print("[verify-notify] 跳过：支付宝密钥未配全。", file=sys.stderr)
        return 2
    if not path.is_file():
        print(f"[verify-notify] 文件不存在：{path}", file=sys.stderr)
        return 2

    body = path.read_text(encoding="utf-8").strip()
    if body.startswith("{"):
        try:
            data = {str(k): str(v) for k, v in json.loads(body).items()}
        except json.JSONDecodeError as e:
            print(f"[verify-notify] JSON 解析失败：{e}", file=sys.stderr)
            return 2
    else:
        data = {k: v for k, v in parse_qsl(body, keep_blank_values=True)}

    signature = data.pop("sign", "")
    if not signature:
        print("[verify-notify] 文件里没有 sign 字段。", file=sys.stderr)
        return 2

    _print_header("Verify Notify")
    print(f"fields  = {sorted(data.keys())}")
    try:
        ok = mp_ali.verify_notify(data, signature)
    except Exception as e:
        print(f"[verify-notify] 验签异常：{e}", file=sys.stderr)
        return 1
    print(f"verified = {ok}")
    return 0 if ok else 1


def _do_page_pay(amount: str, subject: str) -> int:
    from app.infrastructure.payment import alipay as mp_ali

    if not mp_ali.credentials_ready():
        print("[pagepay] 跳过：支付宝密钥未配全，请先设置环境变量。", file=sys.stderr)
        return 2
    if mp_ali.sdk_import_error():
        print(f"[pagepay] 跳过：{mp_ali.sdk_import_error()}", file=sys.stderr)
        return 2

    out_trade_no = f"SANDBOX-PAGE-{uuid.uuid4().hex[:12]}"
    _print_header("Page Pay (alipay.trade.page.pay)")
    print(f"out_trade_no = {out_trade_no}")
    print(f"total_amount = {amount}")
    print(f"subject      = {subject}")
    print(f"debug(sandbox)= {mp_ali.alipay_debug()}")

    res = mp_ali.create_pay_order(
        out_trade_no=out_trade_no,
        total_amount=amount,
        subject=subject,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
    )
    summary = {
        "ok": res.get("ok"),
        "type": res.get("type"),
        "redirect_url": res.get("redirect_url"),
        "qr_code": res.get("qr_code"),
        "message": res.get("message"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if res.get("ok") and res.get("redirect_url"):
        print("\n请复制 redirect_url 到浏览器地址栏打开，即可进入支付宝收银台。")
        print("（该订单号仅用于自测，未写入本地订单文件。）")
        return 0
    return 1


def _do_wap_pay(amount: str, subject: str) -> int:
    from app.infrastructure.payment import alipay as mp_ali

    if not mp_ali.credentials_ready():
        print("[wappay] 跳过：支付宝密钥未配全，请先设置环境变量。", file=sys.stderr)
        return 2
    if mp_ali.sdk_import_error():
        print(f"[wappay] 跳过：{mp_ali.sdk_import_error()}", file=sys.stderr)
        return 2

    out_trade_no = f"SANDBOX-WAP-{uuid.uuid4().hex[:12]}"
    _print_header("Wap Pay (alipay.trade.wap.pay)")
    print(f"out_trade_no = {out_trade_no}")
    print(f"total_amount = {amount}")
    print(f"subject      = {subject}")
    print(f"debug(sandbox)= {mp_ali.alipay_debug()}")

    res = mp_ali.create_pay_order(
        out_trade_no=out_trade_no,
        total_amount=amount,
        subject=subject,
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
    )
    summary = {
        "ok": res.get("ok"),
        "type": res.get("type"),
        "redirect_url": res.get("redirect_url"),
        "qr_code": res.get("qr_code"),
        "message": res.get("message"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if res.get("ok") and res.get("redirect_url"):
        print("\n请复制 redirect_url 到手机浏览器打开，即可唤起支付宝收银台。")
        print("（该订单号仅用于自测，未写入本地订单文件。）")
        return 0
    return 1


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    parser = argparse.ArgumentParser(
        description="支付宝沙箱自测：诊断 / 网站支付 / 订单码 / 离线验签",
    )
    parser.add_argument(
        "--precreate", action="store_true", help="发起一笔 0.01 元沙箱订单码下单（precreate）"
    )
    parser.add_argument(
        "--pagepay", action="store_true", help="发起一笔 0.01 元沙箱电脑网站支付（page.pay）"
    )
    parser.add_argument(
        "--wappay", action="store_true", help="发起一笔 0.01 元沙箱手机网站支付（wap.pay）"
    )
    parser.add_argument(
        "--pay", action="store_true", help="使用自动识别 UA 的 create_pay_order 下单"
    )
    parser.add_argument("--amount", default="0.01", help="金额（元），默认 0.01")
    parser.add_argument("--subject", default="沙箱自测", help="订单 subject")
    parser.add_argument(
        "--verify-notify", metavar="FILE", help="对 form-urlencoded 或 JSON 通知文本离线验签"
    )
    args = parser.parse_args(argv)

    loaded = _load_dotenvs()
    _ensure_repo_on_path()

    _print_header(".env Loaded")
    if loaded:
        for p in loaded:
            print(p)
    else:
        print("（未加载任何 .env；如果你依赖 .env 配置，请确认 python-dotenv 已安装且文件存在。）")

    _print_diagnostics()

    exit_code = 0
    if args.precreate:
        exit_code = _do_precreate(args.amount, args.subject) or exit_code
    if args.pagepay:
        exit_code = _do_page_pay(args.amount, args.subject) or exit_code
    if args.wappay:
        exit_code = _do_wap_pay(args.amount, args.subject) or exit_code
    if args.pay:
        # 默认使用 PC UA 测试
        exit_code = _do_page_pay(args.amount, args.subject) or exit_code
    if args.verify_notify:
        exit_code = _do_verify_notify(Path(args.verify_notify)) or exit_code
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
