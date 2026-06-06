package com.xiuci.xcagi.mobile.core.network

import com.xiuci.xcagi.mobile.BuildConfig
import javax.inject.Inject
import javax.inject.Singleton

enum class ServerMode { LAN, CLOUD }

@Singleton
class ServerRouter @Inject constructor() {
    var fhdHost: String = "127.0.0.1"
    var mode: ServerMode = ServerMode.CLOUD

    fun fhdBaseUrl(): String {
        val host = fhdHost.trim().removePrefix("http://").removePrefix("https://").trimEnd('/')
        val bare = host.substringBefore(':')
        val port = host.substringAfter(':', "").ifBlank { BuildConfig.FHD_DEFAULT_PORT.toString() }
        return "http://$bare:$port/"
    }

    fun modstoreBaseUrl(): String {
        val base = BuildConfig.MODSTORE_BASE_URL.trimEnd('/')
        return "$base/"
    }

    fun activeWriteBaseUrl(): String = when (mode) {
        ServerMode.LAN -> fhdBaseUrl()
        ServerMode.CLOUD -> modstoreBaseUrl()
    }
}
