"""
Dev static file server with long-lived cache headers for webfonts.

Reduces Chrome's "Slow network is detected ... Fallback font" noise when serving
Font Awesome (or similar) from a local dev server on e.g. port 5001.

By default, paths under /api/ are reverse-proxied to the FHD FastAPI app
(http://127.0.0.1:8000) so the frontend can use same-origin URLs like
http://localhost:5001/api/customers/list while you run the API on PORT 8000.

If you see 404 on /api/* from port 5001, you are either not using this script,
used ``--no-api-proxy``, or the API process is not listening on ``--api-backend``.

Usage (from your frontend dist or public folder):
  python scripts/serve_static_cached.py --port 5001 --directory path/to/dist
  # Terminal 2: python -m backend.http_app   (or uvicorn on 8000)
"""

from __future__ import annotations

import argparse
import http.server
import shutil
import socketserver
import urllib.error
import urllib.request
from functools import partial
from pathlib import Path


class CachedStaticHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        path_only = self.path.split("?", 1)[0].lower()
        if path_only.endswith((".woff", ".woff2", ".ttf", ".eot", ".otf")):
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        super().end_headers()


_HOP_BY_HOP = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
)


class DevStaticHandler(CachedStaticHandler):
    """Serves static files; forwards /api/* to api_backend when configured."""

    _API_DISABLED_MSG = (
        "This URL is an API path, but --no-api-proxy is set (or api_backend is empty). "
        "Restart without --no-api-proxy so /api/* is forwarded to the FastAPI app "
        "(default http://127.0.0.1:8000), or point the frontend at that origin directly."
    )

    def _api_path_prefix(self) -> str:
        return self.path.split("?", 1)[0]

    def _should_proxy(self) -> bool:
        backend = getattr(self.server, "api_backend", None)
        if not backend:
            return False
        return self._api_path_prefix().startswith("/api")

    def _proxy_to_backend(self) -> None:
        backend = getattr(self.server, "api_backend", None)
        assert backend
        target = backend.rstrip("/") + self.path
        data: bytes | None = None
        if self.command in ("POST", "PUT", "PATCH"):
            length = int(self.headers.get("Content-Length", 0) or 0)
            data = self.rfile.read(length) if length else b""
        req = urllib.request.Request(target, data=data, method=self.command)
        for key, value in self.headers.items():
            lk = key.lower()
            if lk in _HOP_BY_HOP or lk == "host":
                continue
            req.add_header(key, value)
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() in _HOP_BY_HOP:
                        continue
                    self.send_header(k, v)
                self.end_headers()
                shutil.copyfileobj(resp, self.wfile)
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            for k, v in e.headers.items():
                if k.lower() in _HOP_BY_HOP:
                    continue
                self.send_header(k, v)
            self.end_headers()
            body = e.read()
            if body:
                self.wfile.write(body)
        except urllib.error.URLError as e:
            reason = getattr(e.reason, "winerror", None) or e.reason
            msg = f"API backend not reachable ({backend}): {reason!s}. Start the FastAPI app (e.g. python -m backend.http_app)."
            self.send_response(502, "Bad Gateway")
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(msg.encode("utf-8"))

    def _reject_api_without_proxy(self) -> bool:
        """Avoid misleading 404 from static lookup for /api/* when proxy is off."""
        if getattr(self.server, "api_backend", None):
            return False
        if not self._api_path_prefix().startswith("/api"):
            return False
        self.send_response(503, "API proxy disabled")
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(self._API_DISABLED_MSG.encode("utf-8"))
        return True

    def do_GET(self) -> None:
        if self._should_proxy():
            self._proxy_to_backend()
            return
        if self._reject_api_without_proxy():
            return
        super().do_GET()

    def do_HEAD(self) -> None:
        if self._should_proxy():
            self._proxy_to_backend()
            return
        if self._reject_api_without_proxy():
            return
        super().do_HEAD()

    def do_POST(self) -> None:
        if self._should_proxy():
            self._proxy_to_backend()
            return
        self.send_error(405, "Method not allowed")

    def do_PUT(self) -> None:
        if self._should_proxy():
            self._proxy_to_backend()
            return
        self.send_error(405, "Method not allowed")

    def do_PATCH(self) -> None:
        if self._should_proxy():
            self._proxy_to_backend()
            return
        self.send_error(405, "Method not allowed")

    def do_DELETE(self) -> None:
        if self._should_proxy():
            self._proxy_to_backend()
            return
        self.send_error(405, "Method not allowed")

    def do_OPTIONS(self) -> None:
        if self._should_proxy():
            self._proxy_to_backend()
            return
        super().do_OPTIONS()


class _ApiProxyTCPServer(socketserver.TCPServer):
    allow_reuse_address = True

    def __init__(
        self,
        server_address,
        RequestHandlerClass,
        api_backend: str | None,
        bind_and_activate: bool = True,
    ) -> None:
        self.api_backend = api_backend
        super().__init__(server_address, RequestHandlerClass, bind_and_activate)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default="127.0.0.1", help="Bind address (default 127.0.0.1)")
    p.add_argument("--port", type=int, default=5001, help="TCP port (default 5001)")
    p.add_argument(
        "--directory",
        default=".",
        help="Root directory to serve (default current directory)",
    )
    p.add_argument(
        "--api-backend",
        default="http://127.0.0.1:8000",
        help="Forward /api/* to this origin (default http://127.0.0.1:8000).",
    )
    p.add_argument(
        "--no-api-proxy",
        action="store_true",
        help="Serve only static files; do not proxy /api/*.",
    )
    args = p.parse_args()
    root = str(Path(args.directory).resolve())
    api_backend = None if args.no_api_proxy else str(args.api_backend).strip().rstrip("/") or None
    handler = partial(DevStaticHandler, directory=root)
    with _ApiProxyTCPServer((args.host, args.port), handler, api_backend=api_backend) as httpd:
        extra = f"; /api/* -> {api_backend}" if api_backend else ""
        print(f"Serving {root} at http://{args.host}:{args.port}/{extra}")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
