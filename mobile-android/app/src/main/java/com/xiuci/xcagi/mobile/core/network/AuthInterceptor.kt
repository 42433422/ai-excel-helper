package com.xiuci.xcagi.mobile.core.network

import com.xiuci.xcagi.mobile.BuildConfig
import com.xiuci.xcagi.mobile.core.ProductSkuConfig
import com.xiuci.xcagi.mobile.core.datastore.SessionStore
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthInterceptor @Inject constructor(
    private val sessionStore: SessionStore,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val fhdToken = runBlocking { sessionStore.fhdAccessFlow.first() }
        val marketToken = runBlocking { sessionStore.marketTokenFlow.first() }
        val userId = runBlocking { sessionStore.userIdFlow.first() }
        val url = chain.request().url.toString()
        val modstoreHost = BuildConfig.MODSTORE_BASE_URL.trimEnd('/')
        val isModstore = url.startsWith(modstoreHost)

        val bearer = when {
            isModstore && marketToken.isNotBlank() -> marketToken
            fhdToken.isNotBlank() -> fhdToken
            marketToken.isNotBlank() -> marketToken
            else -> ""
        }

        val builder = chain.request().newBuilder()
            .header("X-XCAGI-Client", "android")
            .header("X-XCAGI-SKU", ProductSkuConfig.sku)
        if (bearer.isNotBlank()) {
            builder.header("Authorization", "Bearer $bearer")
        }
        if (userId > 0) {
            builder.header("X-User-ID", userId.toString())
        }
        return chain.proceed(builder.build())
    }
}
