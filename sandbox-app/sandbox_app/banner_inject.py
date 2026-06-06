"""向 index.html 注入沙盒横幅与 window.__SANDBOX__。"""

from __future__ import annotations

import re

from sandbox_app.sandbox_settings import SANDBOX_URL_PREFIX

# 预留 body 顶内边距，避免 position:fixed 横幅盖住 Vue 顶栏/按钮；略减小字号与 padding 降低遮挡感
_BANNER_CSS = (
    "body{padding-top:34px;box-sizing:border-box}"
    "#xcagi-sandbox-banner{position:fixed;top:0;left:0;right:0;z-index:2147483646;"
    "background:#7c3aed;color:#fff;font:12px/1.35 system-ui,sans-serif;padding:6px 10px;"
    "text-align:center;box-shadow:0 1px 6px rgba(0,0,0,.12)}"
    "#xcagi-sandbox-banner a{color:#e9d5ff;text-decoration:underline}"
)

_BANNER_HTML = (
    '<div id="xcagi-sandbox-banner" role="status">'
    "<strong>沙盒模式</strong> · 数据默认不落生产 · Mod 验证通过后请打包并在完整 FHD 中安装。"
    " <a href=\"https://xiu-ci.com/market\" target=\"_blank\" rel=\"noopener\">修茈市场</a>"
    "</div>"
)

_SCRIPT = (
    "<script>(function(){window.__SANDBOX__=true;"
    "try{document.documentElement.setAttribute('data-xcagi-sandbox','1');}catch(e){}"
    "})();</script>"
)


def _rewrite_absolute_paths(html: str, prefix: str) -> str:
    """把根绝对路径资源改到 prefix 下，便于 nginx /sandbox/ 反代。"""
    if not prefix:
        return html
    p = prefix.rstrip("/")
    if not p.startswith("/"):
        p = "/" + p

    def repl_href(m: re.Match) -> str:
        return m.group(1) + p + m.group(2)

    # href="/assets/ -> href="/sandbox/assets/
    html = re.sub(r'(href=")(/assets/)', repl_href, html)
    html = re.sub(r'(src=")(/assets/)', repl_href, html)
    for sub in ("font-awesome", "startup", "yuangong", "workflow"):
        html = re.sub(rf'(href=")(/{sub}/)', repl_href, html)
        html = re.sub(rf'(src=")(/{sub}/)', repl_href, html)
    html = re.sub(r'(href=")(/vite\.svg)', repl_href, html)
    html = re.sub(r'(src=")(/vite\.svg)', repl_href, html)
    return html


def inject_sandbox_banner(html: str) -> str:
    if "</head>" in html:
        head_inj = f"<style>{_BANNER_CSS}</style>{_SCRIPT}"
        if SANDBOX_URL_PREFIX:
            base = SANDBOX_URL_PREFIX.strip().rstrip("/")
            if not base.startswith("/"):
                base = "/" + base
            head_inj += f'<base href="{base}/">'
        html = html.replace("</head>", head_inj + "</head>", 1)
    if "<body" in html:
        html = re.sub(r"(<body[^>]*>)", r"\1" + _BANNER_HTML, html, count=1)
    else:
        html = _BANNER_HTML + html

    html = _rewrite_absolute_paths(html, SANDBOX_URL_PREFIX)
    return html
