from starlette.types import ASGIApp, Receive, Scope, Send


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                qs = dict(
                    pair.split(b"=", 1)
                    for pair in scope.get("query_string", b"").split(b"&")
                    if b"=" in pair
                )
                is_sandbox = qs.get(b"sandbox") in (b"1", b"true")
                if is_sandbox:
                    security_headers = {
                        b"x-content-type-options": b"nosniff",
                        b"referrer-policy": b"strict-origin-when-cross-origin",
                        b"content-security-policy": b"default-src 'self' 'unsafe-inline' 'unsafe-eval'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self' ws: wss: http: https:; frame-ancestors *;",
                    }
                else:
                    security_headers = {
                        b"x-content-type-options": b"nosniff",
                        b"x-frame-options": b"DENY",
                        b"referrer-policy": b"strict-origin-when-cross-origin",
                        b"content-security-policy": b"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; img-src 'self' data: blob:; font-src 'self' data: https://fonts.gstatic.com; connect-src 'self' ws: wss:",
                    }
                scheme = scope.get("scheme", "http")
                if scheme == "https":
                    security_headers[b"strict-transport-security"] = (
                        b"max-age=31536000; includeSubDomains"
                    )
                for key, value in security_headers.items():
                    headers[key] = value
                message["headers"] = list(headers.items())
            await send(message)

        await self.app(scope, receive, send_with_headers)
