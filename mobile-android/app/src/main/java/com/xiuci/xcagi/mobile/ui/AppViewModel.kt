package com.xiuci.xcagi.mobile.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.xiuci.xcagi.mobile.core.datastore.SessionStore
import com.xiuci.xcagi.mobile.core.model.ListItem
import com.xiuci.xcagi.mobile.core.network.ServerMode
import com.xiuci.xcagi.mobile.core.network.ServerRouter
import com.xiuci.xcagi.mobile.BuildConfig
import com.xiuci.xcagi.mobile.core.model.AppConfigResponse
import com.xiuci.xcagi.mobile.core.observability.XcagiAnalytics
import com.xiuci.xcagi.mobile.core.push.PushRegistrar
import com.xiuci.xcagi.mobile.core.repository.XcagiRepository
import com.xiuci.xcagi.mobile.core.sync.MobileSyncRepository
import com.xiuci.xcagi.mobile.core.work.MobileSyncWorker
import com.xiuci.xcagi.mobile.navigation.Routes
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import android.content.Context
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.Job
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.withTimeout
import javax.inject.Inject

data class UiMessage(val text: String, val isError: Boolean = false)

data class UpdatePrompt(
    val force: Boolean,
    val versionName: String,
    val downloadUrl: String,
)

@HiltViewModel
class AppViewModel @Inject constructor(
    @ApplicationContext private val appContext: Context,
    private val repo: XcagiRepository,
    private val sessionStore: SessionStore,
    private val serverRouter: ServerRouter,
    private val syncRepo: MobileSyncRepository,
    private val pushRegistrar: PushRegistrar,
    private val analytics: XcagiAnalytics,
) : ViewModel() {
    val isLoggedIn = sessionStore.isLoggedInFlow.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), false)
    val isSetupComplete = sessionStore.isSetupCompleteFlow.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), false)
    val autoLanProbe = sessionStore.autoLanProbeFlow.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), false)
    val fhdHost = sessionStore.fhdHostFlow.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), "")

    val displayName = sessionStore.fhdUsernameFlow.stateIn(
        viewModelScope,
        SharingStarted.WhileSubscribed(5_000),
        "",
    )

    val serverModeLabel = combine(sessionStore.serverModeFlow, sessionStore.fhdHostFlow) { mode, host ->
        when {
            mode == "cloud" -> "云端模式"
            host.isNotBlank() -> "局域网 · $host"
            else -> "局域网（未配置电脑）"
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), "云端模式")

    private val _marketAccess = MutableStateFlow("")
    val marketAccess: StateFlow<String> = _marketAccess.asStateFlow()

    private val _marketRefresh = MutableStateFlow("")
    val marketRefresh: StateFlow<String> = _marketRefresh.asStateFlow()

    private val _navReady = MutableStateFlow(false)
    val navReady: StateFlow<Boolean> = _navReady.asStateFlow()

    private val _startRoute = MutableStateFlow(Routes.CONNECT)
    val startRoute: StateFlow<String> = _startRoute.asStateFlow()

    private val _message = MutableStateFlow<UiMessage?>(null)
    val message: StateFlow<UiMessage?> = _message.asStateFlow()

    private val _chatMessages = MutableStateFlow<List<Pair<String, String>>>(emptyList())
    val chatMessages: StateFlow<List<Pair<String, String>>> = _chatMessages.asStateFlow()

    private val _items = MutableStateFlow<List<ListItem>>(emptyList())
    val items: StateFlow<List<ListItem>> = _items.asStateFlow()

    private val _scanResults = MutableStateFlow<List<String>>(emptyList())
    val scanResults: StateFlow<List<String>> = _scanResults.asStateFlow()

    private val _detailJson = MutableStateFlow("")
    val detailJson: StateFlow<String> = _detailJson.asStateFlow()

    private val _streaming = MutableStateFlow(false)
    val streaming: StateFlow<Boolean> = _streaming.asStateFlow()

    private val _listLoading = MutableStateFlow(false)
    val listLoading: StateFlow<Boolean> = _listLoading.asStateFlow()

    private val _listError = MutableStateFlow<String?>(null)
    val listError: StateFlow<String?> = _listError.asStateFlow()

    val isCloudMode = sessionStore.serverModeFlow
        .map { it == "cloud" }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), true)

    val chatConnectionChip = combine(sessionStore.serverModeFlow, sessionStore.fhdHostFlow) { mode, host ->
        when {
            mode == "cloud" -> "云端"
            host.isNotBlank() -> "局域网"
            else -> "未连电脑"
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), "云端")

    private val _homeHub = MutableStateFlow(HomeHubState())
    val homeHub: StateFlow<HomeHubState> = _homeHub.asStateFlow()

    private val _chatSuggestions = MutableStateFlow<List<ChatSuggestion>>(emptyList())
    val chatSuggestions: StateFlow<List<ChatSuggestion>> = _chatSuggestions.asStateFlow()

    private val _chatAction = MutableStateFlow<ChatAction?>(null)
    val chatAction: StateFlow<ChatAction?> = _chatAction.asStateFlow()

    val syncStaleHint = combine(sessionStore.lastSyncAtFlow, sessionStore.fhdHostFlow) { last, host ->
        host.isNotBlank() && last.isBlank()
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), false)

    val canUseNativeChat = sessionStore.fhdAccessFlow
        .map { it.isNotBlank() }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5_000), false)

    val autoSync = sessionStore.autoSyncFlow.stateIn(
        viewModelScope,
        SharingStarted.WhileSubscribed(5_000),
        true,
    )

    private val _appConfig = MutableStateFlow<AppConfigResponse?>(null)
    val appConfig: StateFlow<AppConfigResponse?> = _appConfig.asStateFlow()

    private val _updatePrompt = MutableStateFlow<UpdatePrompt?>(null)
    val updatePrompt: StateFlow<UpdatePrompt?> = _updatePrompt.asStateFlow()

    val biometricEnabled = sessionStore.biometricEnabledFlow.stateIn(
        viewModelScope,
        SharingStarted.WhileSubscribed(5_000),
        false,
    )

    val themeMode = sessionStore.themeModeFlow.stateIn(
        viewModelScope,
        SharingStarted.WhileSubscribed(5_000),
        "system",
    )

    private var chatJob: Job? = null

    init {
        pushRegistrar.initSdk()
        analytics.log("app_open")
        viewModelScope.launch {
            repo.fetchAppConfig().onSuccess {
                _appConfig.value = it
                refreshStartRoute()
            }
            checkForUpdate(manual = false)
            try {
                repo.ensureStandaloneCloudIfFresh()
                val host = sessionStore.fhdHost()
                if (host.isNotBlank()) serverRouter.fhdHost = host
                val mode = sessionStore.serverModeFlow.first()
                serverRouter.mode = if (mode == "cloud") ServerMode.CLOUD else ServerMode.LAN
                if (_appConfig.value == null) refreshStartRoute()
                val (access, refresh) = repo.marketTokensForWeb()
                _marketAccess.value = access
                _marketRefresh.value = refresh
            } catch (_: Exception) {
                refreshStartRoute()
            } finally {
                _navReady.value = true
            }
            try {
                withTimeout(8_000) { refreshMarketTokens() }
            } catch (_: Exception) {
                /* 离线或电脑未开：不阻塞进入 App */
            }
            updateSyncWork(sessionStore.autoSyncFlow.first())
        }
    }

    fun refreshStartRoute() = viewModelScope.launch {
        val cfg = _appConfig.value
        val accepted = sessionStore.legalAcceptedVersion()
        val needLegal = cfg != null && accepted != cfg.legal_version
        if (needLegal) {
            _startRoute.value = Routes.LEGAL
            return@launch
        }
        val setup = sessionStore.isSetupComplete()
        val loggedIn = sessionStore.isLoggedInFlow.first()
        _startRoute.value = when {
            !setup -> Routes.CONNECT
            !loggedIn -> Routes.AUTH
            else -> Routes.HOME_HUB
        }
    }

    fun acceptLegal(onDone: () -> Unit) = viewModelScope.launch {
        val ver = _appConfig.value?.legal_version ?: "1"
        sessionStore.setLegalAcceptedVersion(ver)
        refreshStartRoute()
        onDone()
    }

    fun checkForUpdate(manual: Boolean) = viewModelScope.launch {
        val cfg = _appConfig.value ?: repo.fetchAppConfig().getOrNull().also { _appConfig.value = it } ?: return@launch
        val cur = BuildConfig.VERSION_CODE
        if (cur < cfg.min_android_version || (cfg.force_update && cur < cfg.latest_android_version)) {
            _updatePrompt.value = UpdatePrompt(
                force = true,
                versionName = cfg.latest_android_version_name,
                downloadUrl = cfg.apk_download_url,
            )
        } else if (manual && cur < cfg.latest_android_version) {
            _updatePrompt.value = UpdatePrompt(
                force = false,
                versionName = cfg.latest_android_version_name,
                downloadUrl = cfg.apk_download_url,
            )
        } else if (manual) {
            snack("当前已是最新版本")
        }
    }

    fun dismissUpdatePrompt() {
        _updatePrompt.value = null
    }

    fun setBiometricEnabled(enabled: Boolean) = viewModelScope.launch {
        sessionStore.setBiometricEnabled(enabled)
    }

    fun setThemeMode(mode: String) = viewModelScope.launch {
        sessionStore.setThemeMode(mode)
    }

    fun submitFeedback(message: String, onDone: () -> Unit = {}) = viewModelScope.launch {
        repo.submitFeedback(message).onSuccess {
            snack("感谢反馈")
            onDone()
        }.onFailure { snack(it.message ?: "提交失败", true) }
    }

    fun deleteAccount(password: String, onDone: () -> Unit) = viewModelScope.launch {
        repo.deleteAccount(password).onSuccess {
            pushRegistrar.unregisterAll()
            snack("账号已注销")
            refreshStartRoute()
            onDone()
        }.onFailure { snack(it.message ?: "注销失败", true) }
    }

    fun exportAccount(onPath: (String) -> Unit) = viewModelScope.launch {
        repo.exportAccountData().onSuccess {
            snack("导出数据已就绪")
        }.onFailure { snack(it.message ?: "导出失败", true) }
    }

    fun loadHomeHub() = viewModelScope.launch {
        _homeHub.value = _homeHub.value.copy(loading = true)
        val host = sessionStore.fhdHostFlow.first()
        val online = host.isNotBlank() && repo.checkHealth(host)
        val syncLabel = syncRepo.statusLabel(online)
        val (mods, fromCloud) = if (online) {
            val list = repo.fetchHome().getOrNull()?.let { data ->
                @Suppress("UNCHECKED_CAST")
                val raw = (data["mods"] as? List<Map<String, Any?>>) ?: emptyList()
                raw.mapNotNull { row ->
                    val id = row["id"]?.toString()?.trim().orEmpty()
                    val name = row["name"]?.toString()?.trim().orEmpty()
                    if (id.isNotBlank()) ListItem(id, name.ifBlank { id }) else null
                }
            } ?: repo.mods().getOrElse { emptyList() }
            list to false
        } else {
            repo.marketCatalog().getOrElse { emptyList() } to true
        }
        _homeHub.value = HomeHubState(
            loading = false,
            pcOnline = online,
            mods = mods,
            modsFromCloud = fromCloud,
            syncLabel = syncLabel,
        )
        rebuildChatSuggestions(mods, online)
    }

    private fun rebuildChatSuggestions(mods: List<ListItem>, pcOnline: Boolean) {
        val base = mutableListOf(
            ChatSuggestion("打开工作台", "帮我打开工作台首页"),
            ChatSuggestion("今日待办", "总结我今天的待办和审批"),
        )
        if (pcOnline) {
            base.add(ChatSuggestion("同步状态", "我的手机和电脑数据同步了吗？"))
        }
        mods.take(6).forEach { m ->
            base.add(ChatSuggestion(m.title, "打开 Mod ${m.id} 并说明能做什么"))
        }
        _chatSuggestions.value = base
    }

    fun runSyncNow() = viewModelScope.launch {
        _homeHub.value = _homeHub.value.copy(syncing = true)
        syncRepo.pullAndCache()
            .onSuccess { summary ->
                snack("同步完成")
                _homeHub.value = _homeHub.value.copy(
                    syncing = false,
                    syncLabel = summary.label,
                )
            }
            .onFailure {
                snack(it.message ?: "同步失败", true)
                _homeHub.value = _homeHub.value.copy(syncing = false)
            }
        loadHomeHub()
    }

    fun setAutoSync(enabled: Boolean) = viewModelScope.launch {
        sessionStore.setAutoSync(enabled)
        updateSyncWork(enabled)
    }

    private fun updateSyncWork(enabled: Boolean) {
        val wm = try {
            WorkManager.getInstance(appContext)
        } catch (_: Exception) {
            return
        }
        if (enabled) {
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED)
                .build()
            val req = PeriodicWorkRequestBuilder<MobileSyncWorker>(30, TimeUnit.MINUTES)
                .setConstraints(constraints)
                .build()
            wm.enqueueUniquePeriodicWork(
                "xcagi_mobile_sync",
                ExistingPeriodicWorkPolicy.UPDATE,
                req,
            )
        } else {
            wm.cancelUniqueWork("xcagi_mobile_sync")
        }
    }

    fun workbenchUrl(): String = repo.workbenchHomeUrl()

    fun refreshMarketTokens() = viewModelScope.launch {
        val cloudFirst = sessionStore.serverModeFlow.first() == "cloud"
        if (!cloudFirst && repo.hasNativeFhdAuth()) {
            try {
                kotlinx.coroutines.withTimeout(5_000) { repo.syncMarketSessionHandoff() }
            } catch (_: Exception) {
            }
        }
        val (access, refresh) = repo.marketTokensForWeb()
        _marketAccess.value = access
        _marketRefresh.value = refresh
    }

    fun completeSetup() = viewModelScope.launch {
        sessionStore.setSetupComplete(true)
        refreshStartRoute()
    }

    fun skipToCloud(onDone: () -> Unit) = viewModelScope.launch {
        sessionStore.setSetupComplete(true)
        sessionStore.setServerMode("cloud")
        serverRouter.mode = ServerMode.CLOUD
        snack("已切换云端模式，可登录使用")
        refreshStartRoute()
        onDone()
    }

    fun setAutoLanProbe(enabled: Boolean) = viewModelScope.launch {
        sessionStore.setAutoLanProbe(enabled)
    }

    fun snack(text: String, isError: Boolean = false) { _message.value = UiMessage(text, isError) }
    fun clearSnack() { _message.value = null }

    fun setHost(host: String, markSetup: Boolean = false) = viewModelScope.launch {
        sessionStore.setFhdHost(host)
        serverRouter.fhdHost = host
        if (markSetup) {
            sessionStore.setSetupComplete(true)
            refreshStartRoute()
        }
    }

    fun setMode(cloud: Boolean) = viewModelScope.launch {
        sessionStore.setServerMode(if (cloud) "cloud" else "lan")
        serverRouter.mode = if (cloud) ServerMode.CLOUD else ServerMode.LAN
    }

    fun probeHealth(host: String, onResult: (Boolean) -> Unit) = viewModelScope.launch {
        onResult(repo.checkHealth(host))
    }

    fun scanSubnet(prefix: String) = viewModelScope.launch {
        _scanResults.value = repo.scanLan(prefix)
        snack("发现 ${_scanResults.value.size} 台主机")
    }

    fun loginFhd(u: String, p: String, onDone: (Boolean) -> Unit) = viewModelScope.launch {
        repo.loginUnified(u, p).onSuccess {
            snack("欢迎 $it")
            analytics.log("login_success", mapOf("method" to "password"))
            refreshMarketTokens()
            pushRegistrar.registerAll()
            onDone(true)
        }.onFailure {
            analytics.log("login_fail", mapOf("method" to "password"))
            snack(it.message ?: "失败", true)
            onDone(false)
        }
    }

    fun register(u: String, p: String, e: String, onDone: (Boolean) -> Unit) = viewModelScope.launch {
        repo.register(u, p, e).onSuccess { snack("注册成功"); onDone(true) }
            .onFailure { snack(it.message ?: "失败", true); onDone(false) }
    }

    fun sendCode(phone: String) = viewModelScope.launch {
        repo.sendMarketCode(phone).onSuccess { snack("验证码已发送") }
            .onFailure { snack(it.message ?: "失败", true) }
    }

    fun loginPhone(phone: String, code: String, onDone: (Boolean) -> Unit) = viewModelScope.launch {
        repo.loginMarketPhone(phone, code).onSuccess {
            snack(it)
            analytics.log("login_success", mapOf("method" to "phone"))
            refreshMarketTokens()
            pushRegistrar.registerAll()
            onDone(true)
        }.onFailure {
            analytics.log("login_fail", mapOf("method" to "phone"))
            snack(it.message ?: "失败", true)
            onDone(false)
        }
    }

    fun exchangeQr(nonce: String, onDone: (Boolean) -> Unit) = viewModelScope.launch {
        repo.pairingExchange(nonce).onSuccess { (h, _) ->
            sessionStore.setFhdHost(h)
            serverRouter.fhdHost = h
            sessionStore.setSetupComplete(true)
            refreshStartRoute()
            snack("已绑定 $h")
            onDone(true)
        }.onFailure { snack(it.message ?: "配对失败", true); onDone(false) }
    }

    fun lanRequest(note: String) = viewModelScope.launch {
        repo.requestLanAccess(note).onSuccess { snack(it) }.onFailure { snack(it.message ?: "", true) }
    }

    fun loadChatCache() = viewModelScope.launch {
        _chatMessages.value = repo.loadCachedChat()
    }

    fun sendChat(text: String) {
        chatJob?.cancel()
        _chatAction.value = null
        _chatMessages.value = _chatMessages.value + ("user" to text)
        if (!canUseNativeChat.value) {
            _chatMessages.value = _chatMessages.value + (
                "assistant" to "当前为云端账号，完整 AI 对话需连接电脑端并登录；您可在「工作台」使用网页版 AI。"
            )
            return
        }
        _streaming.value = true
        var acc = ""
        chatJob = viewModelScope.launch {
            if (!repo.hasNativeFhdAuth()) {
                _streaming.value = false
                _chatMessages.value = _chatMessages.value + (
                    "assistant" to "请先使用电脑端账号登录，或在工作台使用云端 AI。"
                )
                return@launch
            }
            repo.streamChat(
                text,
                onToken = { t ->
                    acc += t
                    _chatMessages.value = _chatMessages.value.dropLast(1) + ("assistant" to acc)
                },
                onDone = { full ->
                    _streaming.value = false
                    _chatMessages.value = _chatMessages.value.dropLast(1) + ("assistant" to full)
                    inferChatAction(text, full)
                },
                onError = { e ->
                    _streaming.value = false
                    _chatMessages.value = _chatMessages.value + ("assistant" to "错误: $e")
                },
            )
        }
    }

    private fun inferChatAction(userText: String, reply: String) {
        val lower = (userText + " " + reply).lowercase()
        when {
            lower.contains("工作台") -> _chatAction.value = ChatAction("workbench", label = "工作台")
            lower.contains("审批") -> _chatAction.value = ChatAction("workbench", label = "审批")
            else -> {
                val mod = _homeHub.value.mods.firstOrNull { m ->
                    lower.contains(m.id.lowercase()) || lower.contains(m.title.lowercase())
                }
                if (mod != null) {
                    _chatAction.value = ChatAction("mod", mod.id, mod.title)
                }
            }
        }
    }

    fun clearChatAction() {
        _chatAction.value = null
    }

    fun stopChat() { chatJob?.cancel(); _streaming.value = false }

    private fun loadEnterpriseList(block: suspend () -> Result<List<ListItem>>) = viewModelScope.launch {
        _listLoading.value = true
        _listError.value = null
        block()
            .onSuccess { list ->
                _items.value = list
                if (list.any { it.subtitle.contains("离线缓存") }) {
                    _listError.value = "网络不可用，已显示本地缓存"
                }
            }
            .onFailure { err ->
                _listError.value = err.message ?: "加载失败"
            }
        _listLoading.value = false
    }

    fun loadApprovals() = loadEnterpriseList { repo.approvals() }

    fun loadApprovalDetail(id: Int) = viewModelScope.launch {
        repo.approvalDetail(id).onSuccess { _detailJson.value = it.toString() }
            .onFailure { snack(it.message ?: "", true) }
    }

    fun approve(id: Int, opinion: String, onDone: () -> Unit) = viewModelScope.launch {
        repo.approve(id, opinion).onSuccess { snack("已通过"); onDone() }
            .onFailure { snack(it.message ?: "", true) }
    }

    fun reject(id: Int, reason: String, onDone: () -> Unit) = viewModelScope.launch {
        repo.reject(id, reason).onSuccess { snack("已驳回"); onDone() }
            .onFailure { snack(it.message ?: "", true) }
    }

    fun loadCustomers() = loadEnterpriseList { repo.customers() }

    fun loadShipments() = loadEnterpriseList { repo.shipments() }

    fun loadBridge() = viewModelScope.launch {
        repo.bridgeRequests().onSuccess { _items.value = it }.onFailure { snack(it.message ?: "", true) }
    }

    fun loadMods() = viewModelScope.launch {
        repo.mods().onSuccess { _items.value = it }.onFailure { snack(it.message ?: "", true) }
    }

    fun loadMarket() = viewModelScope.launch {
        repo.marketCatalog().onSuccess { _items.value = it }.onFailure { snack(it.message ?: "", true) }
    }

    fun loadInventory() = viewModelScope.launch {
        _listLoading.value = true
        _listError.value = null
        repo.inventory()
            .onSuccess { lines -> _items.value = lines.map { ListItem(it, it) } }
            .onFailure { err -> _listError.value = err.message ?: "加载失败" }
        _listLoading.value = false
    }

    fun loadFinance() = viewModelScope.launch {
        repo.financeSummary().onSuccess { _detailJson.value = it }
            .onFailure { snack(it.message ?: "", true) }
    }

    suspend fun modUrl(modId: String) = repo.modWebUrl(modId)

    suspend fun modOpensInCloudWorkbench() = repo.modOpensInCloudWorkbench()

    fun requestModOpen(modId: String, onCloud: () -> Unit, onNative: () -> Unit) = viewModelScope.launch {
        if (modOpensInCloudWorkbench()) onCloud() else onNative()
    }

    suspend fun bearerToken(): String {
        val t = sessionStore.fhdAccessFlow.first()
        return if (t.isBlank()) "" else "Bearer $t"
    }

    fun bridgeRespond(id: Int, text: String, onDone: () -> Unit) = viewModelScope.launch {
        repo.bridgeRespond(id, text).onSuccess { snack("已回复"); onDone() }
            .onFailure { snack(it.message ?: "", true) }
    }

    fun logout(onDone: () -> Unit) = viewModelScope.launch {
        pushRegistrar.unregisterAll()
        repo.logout()
        refreshStartRoute()
        onDone()
    }

    fun handleDeepLink(route: String, nav: (String) -> Unit) {
        when {
            route.contains("workbench") -> nav(Routes.WORKBENCH)
            route.contains("chat") -> nav(Routes.CHAT)
            route.contains("approval") -> {
                val id = Regex("approval/(\\d+)").find(route)?.groupValues?.getOrNull(1)
                if (id != null) nav("approval/$id") else nav(Routes.APPROVAL)
            }
            else -> nav(Routes.HOME_HUB)
        }
    }
}
