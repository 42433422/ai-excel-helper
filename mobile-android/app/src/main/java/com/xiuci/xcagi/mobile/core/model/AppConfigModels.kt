package com.xiuci.xcagi.mobile.core.model

data class AppConfigResponse(
    val ok: Boolean = false,
    val privacy_url: String = "",
    val terms_url: String = "",
    val legal_version: String = "1",
    val min_android_version: Int = 0,
    val latest_android_version: Int = 0,
    val latest_android_version_name: String = "",
    val force_update: Boolean = false,
    val apk_download_url: String = "",
    val feedback_email: String = "",
)

data class AccountDeleteBody(val password: String)

data class AppFeedbackBody(
    val message: String,
    val contact: String = "",
    val app_version: String = "",
    val sku: String = "",
    val platform: String = "android",
)

data class DeviceRegisterBody(
    val fcm_token: String,
    val push_provider: String = "fcm",
    val push_token: String = "",
    val product_sku: String = "personal",
    val device_label: String = "",
    val platform: String = "android",
)
