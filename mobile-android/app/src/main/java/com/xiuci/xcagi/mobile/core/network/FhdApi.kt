package com.xiuci.xcagi.mobile.core.network

import com.google.gson.JsonObject
import com.xiuci.xcagi.mobile.core.model.AccessRequestPayload
import com.xiuci.xcagi.mobile.core.model.DeviceRegisterBody
import com.xiuci.xcagi.mobile.core.model.ChatRequest
import com.xiuci.xcagi.mobile.core.model.DiscoverHintData
import com.xiuci.xcagi.mobile.core.model.MobileEnvelope
import com.xiuci.xcagi.mobile.core.model.MobileLoginData
import com.xiuci.xcagi.mobile.core.model.MeData
import okhttp3.ResponseBody
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.Streaming

data class MobileLoginRequest(
    val username: String,
    val password: String,
    val account_kind: String,
)

data class MobileRefreshRequest(val refresh_token: String)

data class RegisterRequest(
    val username: String,
    val password: String,
    val email: String? = null,
    val verification_code: String? = null,
)

data class ApproveBody(val approver_id: Int, val opinion: String = "")
data class RejectBody(val approver_id: Int, val reason: String = "")
data class BridgeRespondBody(val response: String, val responded_by: String? = null, val status: String = "resolved")
data class PairingExchangeBody(val nonce: String)

data class SyncPullBody(val since_cursor: Int = 0)

data class SyncPushItem(
    val entity_type: String,
    val entity_id: String,
    val operation: String = "update",
    val payload: Map<String, Any?> = emptyMap(),
)

data class SyncPushBody(val items: List<SyncPushItem> = emptyList())

interface FhdApi {
    @GET("api/health")
    suspend fun health(): Map<String, Any?>

    @GET("api/mobile/v1/health")
    suspend fun mobileHealth(): MobileEnvelope<Map<String, String>>

    @POST("api/mobile/v1/auth/login")
    suspend fun mobileLogin(@Body body: MobileLoginRequest): MobileEnvelope<MobileLoginData>

    @POST("api/mobile/v1/auth/refresh")
    suspend fun mobileRefresh(@Body body: MobileRefreshRequest): MobileEnvelope<MobileLoginData>

    @GET("api/mobile/v1/host/discover-hint")
    suspend fun discoverHint(): MobileEnvelope<DiscoverHintData>

    @GET("api/mobile/v1/me")
    suspend fun me(): MobileEnvelope<MeData>

    @POST("api/auth/register")
    suspend fun register(@Body body: RegisterRequest): Map<String, Any?>

    @POST("api/lan/access-requests")
    suspend fun lanAccessRequest(@Body body: AccessRequestPayload): Map<String, Any?>

    @GET("api/lan/status")
    suspend fun lanStatus(): Map<String, Any?>

    @POST("api/ai/chat")
    suspend fun chat(@Body body: ChatRequest): Map<String, Any?>

    @Streaming
    @POST("api/ai/chat/stream")
    suspend fun chatStream(@Body body: Map<String, String>): ResponseBody

    @GET("api/mobile/v1/approval/requests")
    suspend fun mobileApprovals(
        @Query("page") page: Int = 1,
        @Query("page_size") pageSize: Int = 50,
    ): MobileEnvelope<Map<String, Any?>>

    @GET("api/approval/requests/{id}")
    suspend fun approvalDetail(@Path("id") id: Int): Map<String, Any?>

    @POST("api/approval/requests/{id}/approve")
    suspend fun approvalApprove(@Path("id") id: Int, @Body body: ApproveBody): Map<String, Any?>

    @POST("api/approval/requests/{id}/reject")
    suspend fun approvalReject(@Path("id") id: Int, @Body body: RejectBody): Map<String, Any?>

    @GET("api/mobile/v1/customers")
    suspend fun mobileCustomers(
        @Query("page") page: Int = 1,
        @Query("per_page") perPage: Int = 20,
    ): MobileEnvelope<Map<String, Any?>>

    @GET("api/mobile/v1/shipments")
    suspend fun mobileShipments(
        @Query("page") page: Int = 1,
        @Query("per_page") perPage: Int = 20,
    ): MobileEnvelope<Map<String, Any?>>

    @GET("api/service-bridge/requests")
    suspend fun bridgeRequests(
        @Query("page") page: Int = 1,
        @Query("per_page") perPage: Int = 20,
    ): Map<String, Any?>

    @PUT("api/service-bridge/requests/{id}/respond")
    suspend fun bridgeRespond(
        @Path("id") id: Int,
        @Body body: BridgeRespondBody,
    ): Map<String, Any?>

    @GET("api/mobile/v1/mods")
    suspend fun mobileMods(): MobileEnvelope<Map<String, Any?>>

    @GET("api/mobile/v1/platform-shell")
    suspend fun mobilePlatformShell(): MobileEnvelope<Map<String, Any?>>

    @GET("api/mobile/v1/home")
    suspend fun mobileHome(): MobileEnvelope<Map<String, Any?>>

    @GET("api/mobile/v1/sync/status")
    suspend fun mobileSyncStatus(): MobileEnvelope<Map<String, Any?>>

    @POST("api/mobile/v1/sync/pull")
    suspend fun mobileSyncPull(@Body body: SyncPullBody): MobileEnvelope<Map<String, Any?>>

    @POST("api/mobile/v1/sync/push")
    suspend fun mobileSyncPush(@Body body: SyncPushBody): MobileEnvelope<Map<String, Any?>>

    @GET("api/mobile/v1/sync/conflicts")
    suspend fun mobileSyncConflicts(): MobileEnvelope<Map<String, Any?>>

    @GET("api/inventory/items")
    suspend fun inventoryItems(): Map<String, Any?>

    @GET("api/mods/")
    suspend fun modsList(): Map<String, Any?>

    @POST("api/mobile/v1/devices/register")
    suspend fun registerDevice(@Body body: DeviceRegisterBody): MobileEnvelope<Map<String, Any?>>

    @POST("api/mobile/v1/pairing/exchange")
    suspend fun pairingExchange(@Body body: PairingExchangeBody): MobileEnvelope<Map<String, Any?>>

    @POST("api/market/account-sync")
    suspend fun marketAccountSync(@Body body: Map<String, String>): Map<String, Any?>

    @GET("api/market/session-handoff")
    suspend fun marketSessionHandoff(): Map<String, Any?>

    @GET("api/finance/summary")
    suspend fun financeSummary(): Map<String, Any?>
}
