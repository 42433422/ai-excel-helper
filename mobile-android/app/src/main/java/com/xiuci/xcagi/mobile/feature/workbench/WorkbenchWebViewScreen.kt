package com.xiuci.xcagi.mobile.feature.workbench

import android.annotation.SuppressLint
import android.graphics.Bitmap
import android.net.Uri
import android.webkit.ValueCallback
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import androidx.browser.customtabs.CustomTabsIntent
import com.xiuci.xcagi.mobile.feature.web.WebViewUrlPolicy
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Box
import com.xiuci.xcagi.mobile.feature.web.buildTokenInjectScript
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView

@SuppressLint("SetJavaScriptEnabled")
@Composable
fun WorkbenchWebViewScreen(
    url: String,
    accessToken: String,
    refreshToken: String,
    onReloadTokens: () -> Unit,
) {
    var loading by remember { mutableStateOf(true) }
    var loadError by remember { mutableStateOf<String?>(null) }
    var webViewRef by remember { mutableStateOf<WebView?>(null) }
    var injectGeneration by remember { mutableIntStateOf(0) }
    var fileCallback by remember { mutableStateOf<ValueCallback<Array<Uri>>?>(null) }
    val filePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        fileCallback?.onReceiveValue(uri?.let { arrayOf(it) })
        fileCallback = null
    }

    if (accessToken.isBlank()) {
        Column(
            Modifier.fillMaxSize().padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = androidx.compose.foundation.layout.Arrangement.Center,
        ) {
            Text("尚未登录市场账号", style = MaterialTheme.typography.titleMedium)
            Text(
                "请使用手机号或电脑端账号登录后再打开工作台。",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 8.dp, bottom = 16.dp),
            )
            Button(onClick = onReloadTokens) { Text("刷新登录态") }
        }
        return
    }

    Box(Modifier.fillMaxSize()) {
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { ctx ->
                WebView(ctx).apply {
                    settings.javaScriptEnabled = true
                    settings.domStorageEnabled = true
                    settings.databaseEnabled = true
                    settings.loadWithOverviewMode = true
                    settings.useWideViewPort = true
                    webChromeClient = object : WebChromeClient() {
                        override fun onShowFileChooser(
                            webView: WebView?,
                            filePathCallback: ValueCallback<Array<Uri>>?,
                            fileChooserParams: FileChooserParams?,
                        ): Boolean {
                            fileCallback?.onReceiveValue(null)
                            fileCallback = filePathCallback
                            filePicker.launch("*/*")
                            return true
                        }
                    }
                    webViewClient = object : WebViewClient() {
                        override fun shouldOverrideUrlLoading(
                            view: WebView?,
                            request: WebResourceRequest?,
                        ): Boolean {
                            val target = request?.url?.toString() ?: return false
                            if (WebViewUrlPolicy.isAllowed(target)) return false
                            CustomTabsIntent.Builder().build().launchUrl(ctx, android.net.Uri.parse(target))
                            return true
                        }

                        override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                            loading = true
                            loadError = null
                        }

                        override fun onPageFinished(view: WebView?, finishedUrl: String?) {
                            loading = false
                            view?.evaluateJavascript(
                                buildTokenInjectScript(accessToken, refreshToken),
                                null,
                            )
                        }

                        override fun onReceivedError(
                            view: WebView?,
                            request: WebResourceRequest?,
                            error: WebResourceError?,
                        ) {
                            if (request?.isForMainFrame == true) {
                                loading = false
                                loadError = error?.description?.toString() ?: "加载失败"
                            }
                        }
                    }
                    webViewRef = this
                    loadUrl(url, mapOf("X-XCAGI-Client" to "android"))
                }
            },
            update = { view ->
                if (injectGeneration > 0) {
                    view.evaluateJavascript(
                        buildTokenInjectScript(accessToken, refreshToken),
                        null,
                    )
                }
            },
        )
        if (loading) {
            CircularProgressIndicator(Modifier.align(Alignment.Center))
        }
        loadError?.let { err ->
            Column(
                Modifier
                    .align(Alignment.BottomCenter)
                    .padding(16.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text(err, color = MaterialTheme.colorScheme.error)
                Button(
                    onClick = {
                        loadError = null
                        loading = true
                        injectGeneration++
                        webViewRef?.reload()
                    },
                    modifier = Modifier.padding(top = 8.dp),
                ) { Text("重试") }
            }
        }
    }
}
