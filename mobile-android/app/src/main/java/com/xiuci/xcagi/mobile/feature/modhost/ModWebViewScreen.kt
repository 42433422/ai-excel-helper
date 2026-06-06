package com.xiuci.xcagi.mobile.feature.modhost

import android.annotation.SuppressLint
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import com.xiuci.xcagi.mobile.feature.web.buildTokenInjectScript
import com.xiuci.xcagi.mobile.feature.web.shouldInjectMarketTokens

@SuppressLint("SetJavaScriptEnabled")
@Composable
fun ModWebViewScreen(
    url: String,
    bearer: String,
    marketAccess: String = "",
    marketRefresh: String = "",
) {
    val injectTokens = shouldInjectMarketTokens(url) && marketAccess.isNotBlank()
    AndroidView(
        modifier = Modifier.fillMaxSize(),
        factory = { ctx ->
            WebView(ctx).apply {
                settings.javaScriptEnabled = true
                settings.domStorageEnabled = true
                webViewClient = object : WebViewClient() {
                    override fun onPageFinished(view: WebView?, finishedUrl: String?) {
                        if (injectTokens) {
                            view?.evaluateJavascript(
                                buildTokenInjectScript(marketAccess, marketRefresh),
                                null,
                            )
                        }
                    }
                }
                val headers = buildMap {
                    put("X-XCAGI-Client", "android")
                    if (bearer.isNotBlank() && !injectTokens) {
                        put("Authorization", bearer)
                    }
                }
                loadUrl(url, headers)
            }
        },
    )
}
