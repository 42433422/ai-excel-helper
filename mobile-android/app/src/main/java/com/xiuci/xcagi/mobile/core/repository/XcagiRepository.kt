package com.xiuci.xcagi.mobile.core.repository

import android.os.Build
import com.xiuci.xcagi.mobile.core.datastore.SessionStore
import com.xiuci.xcagi.mobile.core.db.ApprovalCacheEntity
import com.xiuci.xcagi.mobile.core.db.ChatCacheEntity
import com.xiuci.xcagi.mobile.core.db.ShipmentCacheEntity
import com.xiuci.xcagi.mobile.core.db.XcagiDatabase
import com.xiuci.xcagi.mobile.core.model.AccessRequestPayload
import com.xiuci.xcagi.mobile.core.model.ListItem
import com.xiuci.xcagi.mobile.core.model.MarketAuthResponse
import com.xiuci.xcagi.mobile.core.model.MarketLoginBody
import com.xiuci.xcagi.mobile.core.model.MarketPasswordLoginBody
import com.xiuci.xcagi.mobile.core.model.MarketRegisterBody
import com.xiuci.xcagi.mobile.core.model.MarketSendCodeBody
import com.xiuci.xcagi.mobile.core.network.ApproveBody
import com.xiuci.xcagi.mobile.core.network.BridgeRespondBody
import com.xiuci.xcagi.mobile.core.model.AppConfigResponse
import com.xiuci.xcagi.mobile.core.model.AccountDeleteBody
import com.xiuci.xcagi.mobile.core.model.AppFeedbackBody
import com.xiuci.xcagi.mobile.core.model.DeviceRegisterBody
import com.xiuci.xcagi.mobile.core.network.FhdApi
import com.xiuci.xcagi.mobile.core.network.LanScanner
import com.xiuci.xcagi.mobile.core.network.ModstoreApi
import com.xiuci.xcagi.mobile.core.network.MobileLoginRequest
import com.xiuci.xcagi.mobile.core.network.PairingExchangeBody
import com.xiuci.xcagi.mobile.core.network.RegisterRequest
import com.xiuci.xcagi.mobile.core.network.RejectBody
import com.xiuci.xcagi.mobile.BuildConfig
import com.xiuci.xcagi.mobile.core.ProductSkuConfig
import com.xiuci.xcagi.mobile.core.network.ServerMode
import com.xiuci.xcagi.mobile.core.network.ServerRouter
import com.xiuci.xcagi.mobile.core.network.SseChatClient
import com.google.gson.Gson
import kotlinx.coroutines.flow.first
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class XcagiRepository @Inject constructor(
    private val sessionStore: SessionStore,
    private val serverRouter: ServerRouter,
    private val okHttp: OkHttpClient,
    private val sseChat: SseChatClient,
    private val lanScanner: LanScanner,
    private val db: XcagiDatabase,
    private val gson: Gson = Gson(),
) {
    private var fhdApi: FhdApi? = null
    private var modstoreApi: ModstoreApi? = null
    private var cachedFhdBase: String = ""

    suspend fun syncRouterFromStore() {
        serverRouter.fhdHost = sessionStore.fhdHostFlow.first().ifBlank { "127.0.0.1" }
        var mode = sessionStore.serverModeFlow.first()
        if (mode != "cloud" && sessionStore.fhdHostFlow.first().isBlank()) {
            mode = "cloud"
            sessionStore.setServerMode("cloud")
        }
        serverRouter.mode = if (mode == "cloud") ServerMode.CLOUD else ServerMode.LAN
    }

    /** 未配置电脑时默认云端独立使用，跳过「必须先连电脑」引导。 */
    suspend fun ensureStandaloneCloudIfFresh() {
        if (!sessionStore.isSetupComplete() && sessionStore.fhdHostFlow.first().isBlank()) {
            sessionStore.setSetupComplete(true)
            sessionStore.setServerMode("cloud")
            serverRouter.mode = ServerMode.CLOUD
        }
    }

    private suspend fun isPcReachable(): Boolean {
        syncRouterFromStore()
        if (sessionStore.serverModeFlow.first() == "cloud") return false
        val host = sessionStore.fhdHostFlow.first()
        return host.isNotBlank() && checkHealth(host)
    }

    private suspend fun authHeader(): String {
        val fhd = sessionStore.fhdAccessFlow.first()
        if (fhd.isNotBlank()) return "Bearer $fhd"
        val market = sessionStore.marketAccessToken()
        return if (market.isNotBlank()) "Bearer $market" else ""
    }

    private suspend fun bearer(): String = authHeader()

    suspend fun hasNativeFhdAuth(): Boolean = sessionStore.fhdAccessFlow.first().isNotBlank()

    private suspend fun userId(): Int = sessionStore.userIdFlow.first()

    private suspend fun cachedApprovalItems(): List<ListItem> =
        db.approvalDao().all().mapNotNull { row ->
            try {
                @Suppress("UNCHECKED_CAST")
                val payload = gson.fromJson(row.json, Map::class.java) as? Map<String, Any?> ?: emptyMap()
                ListItem(
                    id = row.requestId.toString(),
                    title = row.title.ifBlank { "审批 #${row.requestId}" },
                    subtitle = listOf(row.status, "离线缓存").filter { it.isNotBlank() }.joinToString(" · "),
                    payload = payload,
                )
            } catch (_: Exception) {
                null
            }
        }

    private suspend fun cachedShipmentItems(): List<ListItem> =
        db.shipmentDao().all().mapNotNull { row ->
            try {
                @Suppress("UNCHECKED_CAST")
                val payload = gson.fromJson(row.json, Map::class.java) as? Map<String, Any?> ?: emptyMap()
                ListItem(
                    id = row.shipmentId.toString(),
                    title = row.orderNumber.ifBlank { "发货 #${row.shipmentId}" },
                    subtitle = listOf(row.status, "离线缓存").filter { it.isNotBlank() }.joinToString(" · "),
                    payload = payload,
                )
            } catch (_: Exception) {
                null
            }
        }

    private fun fhd(): FhdApi {
        val base = serverRouter.fhdBaseUrl()
        if (fhdApi == null || cachedFhdBase != base) {
            cachedFhdBase = base
            fhdApi = Retrofit.Builder().baseUrl(base).client(okHttp)
                .addConverterFactory(GsonConverterFactory.create()).build()
                .create(FhdApi::class.java)
        }
        return fhdApi!!
    }

    private fun modstore(): ModstoreApi {
        val base = serverRouter.modstoreBaseUrl()
        return modstoreApi ?: Retrofit.Builder().baseUrl(base).client(okHttp)
            .addConverterFactory(GsonConverterFactory.create()).build()
            .create(ModstoreApi::class.java).also { modstoreApi = it }
    }

    suspend fun checkHealth(host: String? = null): Boolean {
        syncRouterFromStore()
        val h = host ?: serverRouter.fhdHost
        return lanScanner.probeHealth(h.substringBefore(':').trim())
    }

    suspend fun scanLan(prefix: String): List<String> = lanScanner.scanSubnet(prefix)

    suspend fun loginFhd(username: String, password: String): Result<String> = try {
        syncRouterFromStore()
        val res = fhd().mobileLogin(
            MobileLoginRequest(username, password, ProductSkuConfig.accountKind),
        )
        if (!res.success || res.data?.access_token.isNullOrBlank()) {
            Result.failure(Exception(res.message.ifBlank { "登录失败" }))
        } else {
            val d = res.data!!
            sessionStore.saveFhdAuth(
                d.access_token!!, d.refresh_token ?: "", d.session_id ?: "", d.user?.username ?: username,
                userId = d.user?.id ?: 0,
            )
            refreshMe()
            registerDeviceToken()
            syncMarketSessionHandoff()
            Result.success(d.user?.display_name ?: username)
        }
    } catch (e: Exception) {
        Result.failure(e)
    }

    /** 从 FHD 会话拉取 MODstore token，供工作台 WebView 注入。 */
    suspend fun syncMarketSessionHandoff(): Result<Unit> = try {
        syncRouterFromStore()
        val res = fhd().marketSessionHandoff()
        if (res["success"] == false) {
            Result.failure(Exception(res["message"]?.toString() ?: "未绑定市场账号"))
        } else {
            @Suppress("UNCHECKED_CAST")
            val data = res["data"] as? Map<String, Any?> ?: emptyMap()
            val access = data["market_access_token"]?.toString()?.trim().orEmpty()
            val refresh = data["market_refresh_token"]?.toString()?.trim().orEmpty()
            if (access.isNotBlank()) {
                sessionStore.setMarketTokens(access, refresh)
            }
            Result.success(Unit)
        }
    } catch (e: Exception) {
        Result.failure(e)
    }

    fun workbenchHomeUrl(): String {
        val base = BuildConfig.MODSTORE_BASE_URL.trimEnd('/')
        val sku = BuildConfig.PRODUCT_SKU
        return "$base/workbench/home?client=android&sku=$sku"
    }

    suspend fun marketTokensForWeb(): Pair<String, String> {
        val access = sessionStore.marketAccessToken().ifBlank {
            sessionStore.fhdAccessFlow.first()
        }
        val refresh = sessionStore.marketRefreshToken()
        return access to refresh
    }

    suspend fun register(username: String, password: String, email: String): Result<Unit> {
        syncRouterFromStore()
        return if (isPcReachable()) registerOnPc(username, password, email) else registerOnCloud(username, password, email)
    }

    private suspend fun registerOnPc(username: String, password: String, email: String): Result<Unit> = try {
        val r = fhd().register(RegisterRequest(username, password, email.ifBlank { null }))
        if (r["success"] == false) Result.failure(Exception(r["message"]?.toString() ?: "注册失败"))
        else Result.success(Unit)
    } catch (e: Exception) {
        Result.failure(e)
    }

    private suspend fun registerOnCloud(username: String, password: String, email: String): Result<Unit> {
        if (email.isBlank() || !email.contains("@")) {
            return Result.failure(Exception("云端注册需填写有效邮箱；也可直接使用手机号登录"))
        }
        return try {
            val res = modstore().register(MarketRegisterBody(username, password, email.trim()))
            if (!res.isAuthenticated()) {
                val hint = res.message?.takeIf { it.isNotBlank() }
                    ?: "请先在官网获取邮箱验证码，或改用手机号登录"
                Result.failure(Exception(hint))
            } else {
                applyMarketAuth(res, username)
                Result.success(Unit)
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun refreshMe() {
        try {
            val me = fhd().me()
            val uid = me.data?.user?.id ?: 0
            if (uid > 0) sessionStore.setUserId(uid)
        } catch (_: Exception) {
        }
    }

    suspend fun fetchAppConfig(): Result<AppConfigResponse> = try {
        val cfg = modstore().appConfig(sku = BuildConfig.PRODUCT_SKU)
        Result.success(cfg)
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun deleteAccount(password: String): Result<Unit> = try {
        modstore().deleteAccount(AccountDeleteBody(password))
        logout()
        Result.success(Unit)
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun exportAccountData(): Result<Map<String, Any?>> = try {
        Result.success(modstore().exportAccount())
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun submitFeedback(message: String, contact: String = ""): Result<Unit> = try {
        modstore().submitFeedback(
            AppFeedbackBody(
                message = message,
                contact = contact,
                app_version = BuildConfig.VERSION_NAME,
                sku = BuildConfig.PRODUCT_SKU,
            ),
        )
        Result.success(Unit)
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun registerDeviceToken(
        pushProvider: String = "fcm",
        pushToken: String? = null,
    ) {
        val token = pushToken?.trim().orEmpty().ifBlank { sessionStore.fcmToken() }
        if (token.isBlank()) return
        sessionStore.setFcmToken(token)
        try {
            fhd().registerDevice(
                DeviceRegisterBody(
                    fcm_token = token,
                    push_provider = pushProvider,
                    push_token = token,
                    product_sku = BuildConfig.PRODUCT_SKU,
                    device_label = "Android-${Build.MODEL}",
                ),
            )
        } catch (_: Exception) {
        }
    }

    suspend fun pairingExchange(nonce: String): Result<Pair<String, Int>> = try {
        syncRouterFromStore()
        val r = fhd().pairingExchange(PairingExchangeBody(nonce))
        val d = r.data ?: return Result.failure(Exception(r.message))
        val host = d["host"]?.toString() ?: return Result.failure(Exception("无 host"))
        val port = (d["port"] as? Number)?.toInt() ?: 5000
        sessionStore.setFhdHost(host)
        serverRouter.fhdHost = host
        Result.success(host to port)
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun requestLanAccess(note: String): Result<String> = try {
        syncRouterFromStore()
        fhd().lanAccessRequest(AccessRequestPayload("Android-${Build.MODEL}", note))
        Result.success("已提交 LAN 入网申请")
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun sendMarketCode(phone: String) = try {
        modstore().sendPhoneCode(MarketSendCodeBody(phone))
        Result.success(Unit)
    } catch (e: Exception) {
        Result.failure(e)
    }

    private suspend fun resolveMarketUserIsEnterprise(res: MarketAuthResponse): Boolean {
        res.userIsEnterprise()?.let { return it }
        return try {
            modstore().authMe().is_enterprise
        } catch (_: Exception) {
            false
        }
    }

    private fun validateSkuAccount(isEnterprise: Boolean): Result<Unit> {
        if (ProductSkuConfig.isEnterprise && !isEnterprise) {
            return Result.failure(Exception("该账号为个人账号，请安装并使用「XCAGI 个人版」"))
        }
        if (ProductSkuConfig.isPersonal && isEnterprise) {
            return Result.failure(Exception("该账号为企业账号，请安装并使用「XCAGI 企业版」"))
        }
        return Result.success(Unit)
    }

    private suspend fun applyMarketAuth(res: MarketAuthResponse, displayName: String): Result<String> {
        val token = res.accessToken()
        if (!res.isAuthenticated() || token.isNullOrBlank()) {
            return Result.failure(Exception(res.message ?: "登录失败"))
        }
        sessionStore.setMarketTokens(token, res.refresh_token?.trim().orEmpty())
        val isEnterprise = resolveMarketUserIsEnterprise(res)
        validateSkuAccount(isEnterprise).getOrElse { return Result.failure(it) }
        sessionStore.setDisplayName(displayName)
        sessionStore.setSetupComplete(true)
        sessionStore.setServerMode("cloud")
        serverRouter.mode = ServerMode.CLOUD
        syncRouterFromStore()
        bindMarketTokenToPcIfOnline(token)
        return Result.success("已登录 MODstore（与官网账号互通）")
    }

    /** 电脑在线时把市场 token 写入 FHD 会话，便于局域网能力共用同一账号。 */
    private suspend fun bindMarketTokenToPcIfOnline(marketToken: String) {
        if (!checkHealth()) return
        try {
            val res = fhd().marketAccountSync(mapOf("token" to marketToken))
            if (res["success"] == false) {
                return
            }
        } catch (_: Exception) {
        }
    }

    suspend fun loginMarketPhone(phone: String, code: String): Result<String> = try {
        val res = modstore().loginWithPhoneCode(MarketLoginBody(phone, code))
        applyMarketAuth(res, phone)
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun loginMarketPassword(username: String, password: String): Result<String> = try {
        val res = modstore().loginWithPassword(MarketPasswordLoginBody(username, password))
        applyMarketAuth(res, username)
    } catch (e: Exception) {
        Result.failure(e)
    }

    /**
     * 账号密码登录：电脑在线走 FHD（并 session-handoff 市场 token）；
     * 纯云端走 MODstore 同一套用户名密码。
     */
    suspend fun loginUnified(username: String, password: String): Result<String> {
        syncRouterFromStore()
        return if (isPcReachable()) loginFhd(username, password) else loginMarketPassword(username, password)
    }

    suspend fun streamChat(
        message: String,
        onToken: (String) -> Unit,
        onDone: (String) -> Unit,
        onError: (String) -> Unit,
    ) {
        syncRouterFromStore()
        db.chatDao().insert(ChatCacheEntity(role = "user", text = message))
        val acc = StringBuilder()
        val useCloud = !isPcReachable()
        sseChat.streamChat(
            message,
            authHeader(),
            userId(),
            useCloud = useCloud,
            onToken = { t ->
                acc.append(t)
                onToken(t)
            },
            onDone = { full ->
                val text = full.ifBlank { acc.toString() }
                onDone(text)
            },
            onError = onError,
        )
        val finalText = acc.toString()
        if (finalText.isNotBlank()) {
            db.chatDao().insert(ChatCacheEntity(role = "assistant", text = finalText))
        }
    }

    suspend fun loadCachedChat(): List<Pair<String, String>> =
        db.chatDao().all().map { it.role to it.text }

    suspend fun approvals(): Result<List<ListItem>> {
        val remote = parseMobileList { fhd().mobileApprovals().data }
        remote.getOrNull()?.forEach { item ->
            val rid = item.id.toIntOrNull() ?: return@forEach
            db.approvalDao().insert(
                ApprovalCacheEntity(rid, item.title, item.subtitle, gson.toJson(item.payload)),
            )
        }
        if (remote.isSuccess) return remote
        val cached = cachedApprovalItems()
        return if (cached.isNotEmpty()) Result.success(cached) else remote
    }

    suspend fun approvalDetail(id: Int): Result<Map<String, Any?>> = try {
        syncRouterFromStore()
        Result.success(fhd().approvalDetail(id))
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun approve(id: Int, opinion: String): Result<Unit> = try {
        val uid = userId()
        fhd().approvalApprove(id, ApproveBody(uid, opinion))
        Result.success(Unit)
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun reject(id: Int, reason: String): Result<Unit> = try {
        val uid = userId()
        fhd().approvalReject(id, RejectBody(uid, reason))
        Result.success(Unit)
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun customers(): Result<List<ListItem>> = parseMobileList { fhd().mobileCustomers().data }

    suspend fun shipments(): Result<List<ListItem>> {
        val remote = parseMobileList { fhd().mobileShipments().data }
        remote.getOrNull()?.forEach { item ->
            val sid = item.id.toIntOrNull() ?: return@forEach
            db.shipmentDao().insert(
                ShipmentCacheEntity(sid, item.title, item.subtitle, gson.toJson(item.payload)),
            )
        }
        if (remote.isSuccess) return remote
        val cached = cachedShipmentItems()
        return if (cached.isNotEmpty()) Result.success(cached) else remote
    }
    suspend fun bridgeRequests(): Result<List<ListItem>> = try {
        syncRouterFromStore()
        val res = fhd().bridgeRequests()
        val items = (res["data"] as? List<*>) ?: emptyList<Any>()
        Result.success(items.mapNotNull { row ->
            (row as? Map<*, *>)?.let {
                ListItem(
                    id = "${it["id"]}",
                    title = "${it["title"] ?: ""}",
                    subtitle = "${it["status"] ?: ""}",
                )
            }
        })
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun bridgeRespond(id: Int, text: String): Result<Unit> = try {
        fhd().bridgeRespond(id, BridgeRespondBody(text, "android"))
        Result.success(Unit)
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun mods(): Result<List<ListItem>> = parseMobileList {
        fhd().mobileMods().data
    }

    suspend fun fetchHome(): Result<Map<String, Any?>> = try {
        syncRouterFromStore()
        val res = fhd().mobileHome()
        if (!res.success) Result.failure(Exception(res.message ?: "加载失败"))
        else Result.success(res.data ?: emptyMap())
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun marketCatalog(): Result<List<ListItem>> = try {
        val tok = sessionStore.marketTokenFlow.first().ifBlank { sessionStore.fhdAccessFlow.first() }
        val auth = if (tok.isNotBlank()) "Bearer $tok" else null
        val res = modstore().marketCatalog(auth)
        val items = (res["items"] as? List<*>) ?: emptyList<Any>()
        Result.success(items.mapNotNull { row ->
            (row as? Map<*, *>)?.let {
                ListItem("${it["id"]}", "${it["name"] ?: it["title"]}")
            }
        })
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun inventory(): Result<List<String>> = try {
        syncRouterFromStore()
        val res = fhd().inventoryItems()
        val items = (res["data"] as? List<*>) ?: (res["items"] as? List<*>) ?: emptyList<Any>()
        Result.success(items.map { it.toString() })
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun financeSummary(): Result<String> = try {
        syncRouterFromStore()
        Result.success(fhd().financeSummary().toString())
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun modWebUrl(modId: String): String {
        val online = sessionStore.fhdHostFlow.first().isNotBlank() && checkHealth()
        return if (online) {
            "${serverRouter.fhdBaseUrl()}mod/$modId/"
        } else {
            val base = BuildConfig.MODSTORE_BASE_URL.trimEnd('/')
            "$base/workbench/mod/$modId?client=android"
        }
    }

    suspend fun modOpensInCloudWorkbench(): Boolean {
        val online = sessionStore.fhdHostFlow.first().isNotBlank() && checkHealth()
        return !online
    }

    suspend fun logout() {
        sessionStore.clear()
        db.chatDao().clear()
        db.approvalDao().clear()
        db.shipmentDao().clear()
    }

    private suspend fun parseMobileList(
        loader: suspend () -> Map<String, Any?>?,
    ): Result<List<ListItem>> = try {
        syncRouterFromStore()
        val data = loader() ?: emptyMap()
        val items = (data["items"] as? List<*>) ?: emptyList<Any>()
        Result.success(items.mapNotNull { row ->
            when (row) {
                is Map<*, *> -> ListItem(
                    id = "${row["id"]}",
                    title = "${row["title"] ?: row["name"] ?: row["order_number"]}",
                    subtitle = "${row["status"] ?: ""}",
                    payload = @Suppress("UNCHECKED_CAST") (row as? Map<String, Any?>) ?: emptyMap(),
                )
                else -> null
            }
        })
    } catch (e: Exception) {
        Result.failure(e)
    }
}
