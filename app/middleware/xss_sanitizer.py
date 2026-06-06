import html
import json
import re

from starlette.types import ASGIApp, Receive, Scope, Send

_SCRIPT_RE = re.compile(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", re.IGNORECASE | re.DOTALL)


def _sanitize_value(value):
    if isinstance(value, str):
        value = _SCRIPT_RE.sub("", value)
        return html.escape(value)
    if isinstance(value, dict):
        return {k: _sanitize_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    return value


class XSSSanitizerMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")
        if method in ("GET", "HEAD", "OPTIONS"):
            await self.app(scope, receive, send)
            return

        headers_dict = {}
        for key, value in scope.get("headers", []):
            headers_dict[key.decode("latin-1").lower()] = value.decode("latin-1")

        content_type = headers_dict.get("content-type", "")
        if "json" not in content_type:
            await self.app(scope, receive, send)
            return

        body_parts = []
        body_size = 0

        async def receive_body():
            nonlocal body_size
            while True:
                message = await receive()
                if message["type"] == "http.request":
                    body = message.get("body", b"")
                    body_parts.append(body)
                    body_size += len(body)
                    if not message.get("more_body", False):
                        break
                elif message["type"] == "http.disconnect":
                    return message
            return {"type": "http.request", "body": b"".join(body_parts)}

        message = await receive_body()
        if message.get("type") == "http.disconnect":
            await self.app(scope, receive, send)
            return

        raw_body = message.get("body", b"")
        if raw_body:
            try:
                data = json.loads(raw_body)
                sanitized = _sanitize_value(data)
                new_body = json.dumps(sanitized).encode("utf-8")

                body_sent = False

                async def sanitized_receive():
                    nonlocal body_sent
                    if not body_sent:
                        body_sent = True
                        return {"type": "http.request", "body": new_body, "more_body": False}
                    # Keep StreamingResponse alive by waiting for a real client disconnect
                    # instead of repeatedly returning http.request or a synthetic disconnect.
                    while True:
                        next_message = await receive()
                        if next_message.get("type") == "http.disconnect":
                            return next_message

                await self.app(scope, sanitized_receive, send)
                return
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        await self.app(scope, receive, send)
