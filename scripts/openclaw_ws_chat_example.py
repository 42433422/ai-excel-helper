#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Gateway WebSocket：challenge → connect → chat.send → 接收事件。

与当前 OpenClaw 网关实现一致（部分网络文档已过时）：
  • connect.params.client.id / mode 必须是网关枚举；无 device 时不要写半套 device。
  • 无 device 时需用 openclaw-control-ui + ui 才会保留 operator scopes；纯 cli 会被 clearUnboundScopes。
  • 非浏览器客户端建议带 Origin: http://localhost，且网关需 gateway.controlUi.allowInsecureAuth=true，
    WebSocket 请用 ws://localhost:端口/ws（与浏览器 Secure Context / 本机联调一致）。
  • chat.send 在当前 schema 下需要 sessionKey、message、idempotencyKey（均为必填）。
  • 流式/结束为 type=event, event=chat（payload.state=delta|final|error），不是 chat.progress/chat.done。

依赖:
  pip install websockets

环境变量:
  OPENCLAW_GATEWAY_TOKEN   必填
  OPENCLAW_WS_URL          默认 ws://localhost:28789/ws
  OPENCLAW_SESSION_KEY     默认 main

示例:
  set OPENCLAW_GATEWAY_TOKEN=你的token
  python scripts/openclaw_ws_chat_example.py 你好
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid


def _extract_assistant_text(payload: dict) -> str:
    msg = payload.get("message") or {}
    parts = msg.get("content")
    if not isinstance(parts, list):
        return ""
    out = []
    for block in parts:
        if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str):
            out.append(block["text"])
    return "".join(out)


async def chat_once(message: str) -> int:
    uri = os.environ.get("OPENCLAW_WS_URL", "ws://localhost:28789/ws").strip()
    token = (os.environ.get("OPENCLAW_GATEWAY_TOKEN") or "").strip()
    if not token:
        print("缺少环境变量 OPENCLAW_GATEWAY_TOKEN", file=sys.stderr)
        return 2

    session_key = (os.environ.get("OPENCLAW_SESSION_KEY") or "main").strip()
    # 与网关 checkBrowserOrigin + 本机 loopback 放行一致；无 Origin 时 Control UI 会报 origin missing
    origin = os.environ.get("OPENCLAW_WS_ORIGIN", "http://localhost").strip()

    try:
        import websockets
    except ImportError:
        print("请先安装: pip install websockets", file=sys.stderr)
        return 2

    extra_headers = [("Origin", origin)]

    async with websockets.connect(uri, additional_headers=extra_headers) as ws:
        raw = await ws.recv()
        challenge = json.loads(raw)
        if challenge.get("event") != "connect.challenge":
            print("预期 connect.challenge，收到:", raw[:500], file=sys.stderr)
            return 1

        nonce = challenge["payload"]["nonce"]
        ts = challenge["payload"]["ts"]

        connect_id = str(uuid.uuid4())
        connect_req = {
            "type": "req",
            "id": connect_id,
            "method": "connect",
            "params": {
                "minProtocol": 3,
                "maxProtocol": 3,
                "client": {
                    "id": "openclaw-control-ui",
                    "version": "1.0.0",
                    "platform": "windows",
                    "mode": "ui",
                },
                "role": "operator",
                "scopes": [
                    "operator.read",
                    "operator.write",
                    "operator.approvals",
                    "operator.pairing",
                ],
                "caps": [],
                "commands": [],
                "permissions": {},
                "auth": {"token": token},
                "locale": "zh-CN",
                "userAgent": "openclaw_ws_chat_example/1.0",
            },
        }
        await ws.send(json.dumps(connect_req))

        raw = await ws.recv()
        hello = json.loads(raw)
        if not hello.get("ok"):
            print("握手失败:", json.dumps(hello, ensure_ascii=False, indent=2))
            return 1
        payload = hello.get("payload") or {}
        if payload.get("type") != "hello-ok":
            print("非 hello-ok:", json.dumps(hello, ensure_ascii=False, indent=2))
            return 1
        print("握手成功 (hello-ok)")

        chat_id = str(uuid.uuid4())
        idempotency_key = str(uuid.uuid4())
        chat_req = {
            "type": "req",
            "id": chat_id,
            "method": "chat.send",
            "params": {
                "sessionKey": session_key,
                "message": message,
                "idempotencyKey": idempotency_key,
            },
        }
        await ws.send(json.dumps(chat_req))
        print("已发送 chat.send:", message)

        assistant_buffer = ""
        while True:
            raw = await ws.recv()
            msg = json.loads(raw)

            if msg.get("type") == "res" and msg.get("id") == chat_id:
                if msg.get("ok"):
                    body = msg.get("payload") or {}
                    print("chat.send 确认:", json.dumps(body, ensure_ascii=False))
                else:
                    print("chat.send 错误:", json.dumps(msg.get("error"), ensure_ascii=False))
                # 模型仍会通过 event:chat 推流；继续读直到 final/error
                continue

            if msg.get("type") == "event" and msg.get("event") == "chat":
                p = msg.get("payload") or {}
                state = p.get("state")
                if state == "error":
                    print("\n对话错误:", p.get("errorMessage"))
                    return 1
                text = _extract_assistant_text(p)
                if text:
                    if text != assistant_buffer:
                        assistant_buffer = text
                        print("\r助手: " + text, end="", flush=True)
                if state == "final":
                    print()
                    print("完成 (final)")
                    return 0
                continue

            # 其它事件（agent、tick 等）可忽略或打印调试
            # print("event:", msg.get("type"), msg.get("event") or msg.get("method"))


def main() -> int:
    p = argparse.ArgumentParser(description="OpenClaw WebSocket chat.send 示例")
    p.add_argument("message", nargs="?", default="你好", help="要发送的文本")
    args = p.parse_args()
    try:
        return asyncio.run(chat_once(args.message))
    except KeyboardInterrupt:
        print("\n中断", file=sys.stderr)
        return 130
    except Exception as e:
        print(type(e).__name__, e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
