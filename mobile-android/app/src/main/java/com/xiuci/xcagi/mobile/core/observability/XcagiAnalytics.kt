package com.xiuci.xcagi.mobile.core.observability

import android.content.Context
import android.os.Bundle
import com.google.firebase.analytics.FirebaseAnalytics
import com.xiuci.xcagi.mobile.core.ProductSkuConfig
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class XcagiAnalytics @Inject constructor(
    @ApplicationContext context: Context,
) {
    private val firebase: FirebaseAnalytics? = try {
        FirebaseAnalytics.getInstance(context)
    } catch (_: Exception) {
        null
    }

    fun log(event: String, params: Map<String, String> = emptyMap()) {
        val bundle = Bundle()
        params.forEach { (k, v) -> bundle.putString(k, v) }
        bundle.putString("sku", ProductSkuConfig.sku)
        firebase?.logEvent(event, bundle)
    }
}
