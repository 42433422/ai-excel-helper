package com.xiuci.xcagi.mobile.feature.web

import android.net.Uri
import com.xiuci.xcagi.mobile.BuildConfig

object WebViewUrlPolicy {
    private val allowedHosts = setOf(
        "xiu-ci.com",
        "www.xiu-ci.com",
    )

    fun isAllowed(url: String, extraLanHost: String? = null): Boolean {
        val uri = Uri.parse(url)
        val host = uri.host?.lowercase() ?: return false
        if (allowedHosts.any { host == it || host.endsWith(".$it") }) return true
        val lan = extraLanHost?.substringBefore(':')?.trim()?.lowercase()
        if (!lan.isNullOrBlank() && host == lan) return true
        if (host == "127.0.0.1" || host.startsWith("192.168.")) return true
        return false
    }

    fun modstoreHost(): String = Uri.parse(BuildConfig.MODSTORE_BASE_URL).host.orEmpty()
}
