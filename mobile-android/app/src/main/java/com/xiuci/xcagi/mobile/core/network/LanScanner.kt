package com.xiuci.xcagi.mobile.core.network

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.util.concurrent.TimeUnit
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class LanScanner @Inject constructor() {
    private val probeClient = OkHttpClient.Builder()
        .connectTimeout(2, TimeUnit.SECONDS)
        .readTimeout(2, TimeUnit.SECONDS)
        .build()

    suspend fun scanSubnet(prefix: String, port: Int = 5000): List<String> = withContext(Dispatchers.IO) {
        coroutineScope {
            (1..254).map { host ->
                async {
                    val ip = "$prefix.$host"
                    if (probeHealth(ip, port)) ip else null
                }
            }.awaitAll().filterNotNull().sorted()
        }
    }

    fun probeHealth(host: String, port: Int = 5000): Boolean {
        return try {
            val url = "http://$host:$port/api/health"
            val req = Request.Builder().url(url).get().build()
            probeClient.newCall(req).execute().use { it.isSuccessful }
        } catch (_: Exception) {
            false
        }
    }
}
