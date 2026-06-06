package com.xiuci.xcagi.mobile.core.model

import com.google.gson.JsonElement

data class MobileEnvelope<T>(
    val code: Int = 200,
    val message: String = "",
    val success: Boolean = true,
    val data: T? = null,
)

data class UserDto(
    val id: Int = 0,
    val username: String = "",
    val display_name: String = "",
    val email: String = "",
    val role: String = "",
    val is_active: Boolean = true,
)

data class MobileLoginData(
    val user: UserDto? = null,
    val session_id: String? = null,
    val access_token: String? = null,
    val refresh_token: String? = null,
    val account_kind: String? = null,
    val expires_in: Int? = null,
)

data class MeData(
    val user: UserDto? = null,
    val permissions: List<String>? = null,
    val account_kind: String? = null,
    val company_brand: String? = null,
    val mods: List<ModSummary>? = null,
)

data class ModSummary(val id: String = "")

data class DiscoverHintData(
    val lan: LanHostInfo? = null,
    val instance_name: String? = null,
    val api_port: Int? = null,
    val company: String? = null,
    val brand_url: String? = null,
)

data class LanHostInfo(
    val enabled: Boolean = false,
    val ip: String? = null,
    val is_admin_host: Boolean = false,
)

data class AccessRequestPayload(
    val device_label: String = "",
    val note: String = "",
)

data class ChatRequest(
    val message: String,
    val session_id: String? = null,
)

data class ChatResponse(
    val success: Boolean = false,
    val reply: String? = null,
    val message: String? = null,
    val data: JsonElement? = null,
)

data class ApprovalItem(
    val id: Int = 0,
    val title: String = "",
    val status: String = "",
    val requester: String = "",
    val created_at: String? = null,
)

data class ApprovalListResponse(
    val success: Boolean = false,
    val data: List<ApprovalItem>? = null,
    val items: List<ApprovalItem>? = null,
)

data class CustomerItem(
    val id: Int = 0,
    val name: String = "",
    val phone: String? = null,
)

data class ShipmentItem(
    val id: Int = 0,
    val order_number: String? = null,
    val status: String? = null,
)

data class MarketLoginBody(
    val phone: String,
    val code: String,
)

data class MarketPasswordLoginBody(
    val username: String,
    val password: String,
)

data class MarketSendCodeBody(val phone: String)

data class MarketRegisterBody(
    val username: String,
    val password: String,
    val email: String,
    val verification_code: String = "",
)

data class MarketUserInfo(
    val id: Int? = null,
    val username: String? = null,
    val is_enterprise: Boolean? = null,
)

data class MarketAuthResponse(
    val success: Boolean = false,
    val ok: Boolean = false,
    val token: String? = null,
    val access_token: String? = null,
    val refresh_token: String? = null,
    val message: String? = null,
    val user: MarketUserInfo? = null,
) {
    fun isAuthenticated(): Boolean = success || ok

    fun accessToken(): String? =
        access_token?.trim()?.takeIf { it.isNotBlank() }
            ?: token?.trim()?.takeIf { it.isNotBlank() }

    fun userIsEnterprise(): Boolean? = user?.is_enterprise
}

data class MarketMeResponse(
    val id: Int? = null,
    val username: String? = null,
    val is_enterprise: Boolean = false,
)

data class MarketItem(
    val id: String = "",
    val name: String = "",
    val description: String? = null,
)
