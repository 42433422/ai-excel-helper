package com.xiuci.xcagi.mobile.feature.web

fun buildTokenInjectScript(accessToken: String, refreshToken: String): String {
    fun esc(s: String) = s.replace("\\", "\\\\").replace("'", "\\'")
    val refreshLine = if (refreshToken.isNotBlank()) {
        "localStorage.setItem('modstore_refresh_token','${esc(refreshToken)}');"
    } else {
        ""
    }
    return """
        (function() {
          try {
            localStorage.setItem('modstore_token','${esc(accessToken)}');
            $refreshLine
            window.__XCAGI_CLIENT__ = 'android';
            document.documentElement.classList.add('xcagi-client-android');
            window.dispatchEvent(new Event('xcagi-client-ready'));
          } catch (e) {}
        })();
    """.trimIndent()
}

fun shouldInjectMarketTokens(url: String): Boolean =
    url.contains("xiu-ci.com", ignoreCase = true)
