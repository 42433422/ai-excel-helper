package com.xiuci.xcagi.mobile.navigation

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Chat
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Lan
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Task
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.platform.LocalContext
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import com.xiuci.xcagi.mobile.core.work.LanProbeWorker
import java.util.concurrent.TimeUnit
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.xiuci.xcagi.mobile.R
import com.xiuci.xcagi.mobile.core.ProductSkuConfig
import com.xiuci.xcagi.mobile.core.connectivity.NetworkMonitor
import com.xiuci.xcagi.mobile.feature.legal.LegalConsentScreen
import com.xiuci.xcagi.mobile.feature.modhost.ModWebViewScreen
import com.xiuci.xcagi.mobile.feature.settings.SettingsScreen
import com.xiuci.xcagi.mobile.feature.workbench.WorkbenchWebViewScreen
import com.xiuci.xcagi.mobile.ui.AppViewModel
import android.content.Intent
import android.net.Uri
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.TextButton
import androidx.hilt.navigation.compose.hiltViewModel
import dagger.hilt.android.EntryPointAccessors
import dagger.hilt.EntryPoint
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

@EntryPoint
@InstallIn(SingletonComponent::class)
interface NetworkEntryPoint {
    fun networkMonitor(): NetworkMonitor
}

@Composable
fun XcagiNavHost(vm: AppViewModel, pendingDeepLink: String? = null) {
    val nav = rememberNavController()
    val snack = remember { SnackbarHostState() }
    val msg by vm.message.collectAsState()
    val loggedIn by vm.isLoggedIn.collectAsState()
    val setupComplete by vm.isSetupComplete.collectAsState()
    val autoLanProbe by vm.autoLanProbe.collectAsState()
    val navReady by vm.navReady.collectAsState()
    val startRoute by vm.startRoute.collectAsState()
    val updatePrompt by vm.updatePrompt.collectAsState()
    val ctx = LocalContext.current
    val networkMonitor = androidx.compose.runtime.remember(ctx) {
        EntryPointAccessors.fromApplication(ctx.applicationContext, NetworkEntryPoint::class.java)
            .networkMonitor()
    }
    val online by networkMonitor.online.collectAsState(initial = true)

    LaunchedEffect(pendingDeepLink, loggedIn) {
        if (loggedIn && !pendingDeepLink.isNullOrBlank()) {
            vm.handleDeepLink(pendingDeepLink) { route ->
                nav.navigate(route) { launchSingleTop = true }
            }
        }
    }

    updatePrompt?.let { prompt ->
        AlertDialog(
            onDismissRequest = { if (!prompt.force) vm.dismissUpdatePrompt() },
            title = { Text(if (prompt.force) "需要更新" else "发现新版本") },
            text = { Text("最新版本 ${prompt.versionName}，请更新以获得完整功能与安全修复。") },
            confirmButton = {
                TextButton({
                    ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(prompt.downloadUrl)))
                    if (!prompt.force) vm.dismissUpdatePrompt()
                }) { Text("去更新") }
            },
            dismissButton = if (!prompt.force) {
                { TextButton({ vm.dismissUpdatePrompt() }) { Text("稍后") } }
            } else {
                null
            },
        )
    }

    LaunchedEffect(autoLanProbe) {
        try {
            val wm = WorkManager.getInstance(ctx)
            if (autoLanProbe) {
                val req = PeriodicWorkRequestBuilder<LanProbeWorker>(15, TimeUnit.MINUTES).build()
                wm.enqueueUniquePeriodicWork(
                    "xcagi_lan_probe",
                    ExistingPeriodicWorkPolicy.UPDATE,
                    req,
                )
            } else {
                wm.cancelUniqueWork("xcagi_lan_probe")
            }
        } catch (_: Exception) {
            /* WorkManager 未初始化时不影响主流程 */
        }
    }

    LaunchedEffect(msg) {
        msg?.let { snack.showSnackbar(it.text); vm.clearSnack() }
    }

    LaunchedEffect(loggedIn) {
        if (loggedIn) {
            val r = nav.currentDestination?.route
            if (r == Routes.AUTH || r == Routes.CONNECT || r == Routes.REGISTER) {
                nav.navigate(Routes.HOME_HUB) { popUpTo(nav.graph.findStartDestination().id) { inclusive = true } }
            }
        }
    }

    val backStack by nav.currentBackStackEntryAsState()
    val current = backStack?.destination?.route
    val bottomNavRoutes = if (ProductSkuConfig.showsEnterpriseNav) {
        setOf(Routes.HOME_HUB, Routes.CHAT, Routes.WORKBENCH, Routes.APPROVAL, Routes.ERP, Routes.PROFILE)
    } else {
        setOf(Routes.HOME_HUB, Routes.CHAT, Routes.WORKBENCH, Routes.PROFILE)
    }
    val showBar = loggedIn && current in bottomNavRoutes

    if (!navReady) {
        Box(Modifier.fillMaxSize(), contentAlignment = androidx.compose.ui.Alignment.Center) {
            CircularProgressIndicator()
        }
        return
    }

    Scaffold(
        snackbarHost = { SnackbarHost(snack) },
        topBar = {
            if (!online) {
                androidx.compose.material3.Surface(color = MaterialTheme.colorScheme.errorContainer) {
                    Text(
                        "当前无网络连接",
                        modifier = Modifier.fillMaxWidth().padding(8.dp),
                        color = MaterialTheme.colorScheme.onErrorContainer,
                        style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
        },
        bottomBar = {
            if (showBar) {
                NavigationBar {
                    NavigationBarItem(
                        current == Routes.HOME_HUB,
                        { nav.navigate(Routes.HOME_HUB) { launchSingleTop = true } },
                        icon = { Icon(Icons.Default.Home, null) },
                        label = { Text("首页") },
                    )
                    NavigationBarItem(
                        current == Routes.CHAT,
                        { nav.navigate(Routes.CHAT) { launchSingleTop = true } },
                        icon = { Icon(Icons.Default.Chat, null) },
                        label = { Text("对话") },
                    )
                    NavigationBarItem(
                        current == Routes.WORKBENCH,
                        { nav.navigate(Routes.WORKBENCH) { launchSingleTop = true } },
                        icon = { Icon(Icons.Default.Dashboard, null) },
                        label = { Text("工作台") },
                    )
                    if (ProductSkuConfig.showsEnterpriseNav) {
                        NavigationBarItem(
                            current == Routes.APPROVAL,
                            { nav.navigate(Routes.APPROVAL) { launchSingleTop = true } },
                            icon = { Icon(Icons.Default.Task, null) },
                            label = { Text("审批") },
                        )
                        NavigationBarItem(
                            current == Routes.ERP,
                            { nav.navigate(Routes.ERP) { launchSingleTop = true } },
                            icon = { Icon(Icons.Default.Lan, null) },
                            label = { Text("业务") },
                        )
                    }
                    NavigationBarItem(
                        current == Routes.PROFILE,
                        { nav.navigate(Routes.PROFILE) { launchSingleTop = true } },
                        icon = { Icon(Icons.Default.Person, null) },
                        label = { Text("我的") },
                    )
                }
            }
        },
    ) { padding ->
        NavHost(
            nav,
            startDestination = startRoute,
            Modifier.padding(padding),
        ) {
            composable(Routes.LEGAL) {
                LegalConsentScreen(
                    vm,
                    onAccepted = {
                        nav.navigate(Routes.CONNECT) {
                            popUpTo(Routes.LEGAL) { inclusive = true }
                        }
                    },
                    onAbout = { nav.navigate(Routes.ABOUT) },
                )
            }
            composable(Routes.CONNECT) {
                ConnectScreen(
                    vm,
                    fromProfile = false,
                    onNext = {
                        vm.completeSetup()
                        nav.navigate(Routes.AUTH) { popUpTo(Routes.CONNECT) { inclusive = true } }
                    },
                    onScan = { nav.navigate(Routes.SCAN_QR) },
                    onSkipCloud = {
                        vm.skipToCloud {
                            nav.navigate(Routes.AUTH) { popUpTo(Routes.CONNECT) { inclusive = true } }
                        }
                    },
                    onBack = null,
                )
            }
            composable(Routes.CONNECT_PC) {
                ConnectScreen(
                    vm,
                    fromProfile = true,
                    onNext = { nav.popBackStack() },
                    onScan = { nav.navigate(Routes.SCAN_QR) },
                    onSkipCloud = { nav.popBackStack() },
                    onBack = { nav.popBackStack() },
                )
            }
            composable(Routes.SCAN_QR) {
                com.xiuci.xcagi.mobile.feature.scan.ScanQrScreen(vm) { nav.popBackStack() }
            }
            composable(Routes.SETTINGS) {
                SettingsScreen(vm) { nav.popBackStack() }
            }
            composable(Routes.AUTH) {
                AuthScreen(vm, { nav.navigate(Routes.REGISTER) }, { nav.navigate(Routes.HOME_HUB) })
            }
            composable(Routes.REGISTER) { RegisterScreen(vm) { nav.popBackStack() } }
            composable(Routes.HOME_HUB) {
                HomeHubScreen(
                    vm,
                    onChat = { nav.navigate(Routes.CHAT) },
                    onWorkbench = { nav.navigate(Routes.WORKBENCH) },
                    onConnectPc = { nav.navigate(Routes.CONNECT_PC) },
                    onModClick = { id ->
                        vm.requestModOpen(
                            id,
                            onCloud = { nav.navigate(Routes.WORKBENCH) },
                            onNative = { nav.navigate("mod/$id") },
                        )
                    },
                )
            }
            composable(Routes.WORKBENCH) {
                val access by vm.marketAccess.collectAsState()
                val refresh by vm.marketRefresh.collectAsState()
                LaunchedEffect(Unit) { vm.refreshMarketTokens() }
                WorkbenchWebViewScreen(
                    url = vm.workbenchUrl(),
                    accessToken = access,
                    refreshToken = refresh,
                    onReloadTokens = { vm.refreshMarketTokens() },
                )
            }
            composable(Routes.PROFILE) {
                ProfileScreen(
                    vm,
                    onConnectPc = { nav.navigate(Routes.CONNECT_PC) },
                    onAbout = { nav.navigate(Routes.ABOUT) },
                    onSettings = { nav.navigate(Routes.SETTINGS) },
                    onBridge = { nav.navigate(Routes.BRIDGE) },
                    onMods = { nav.navigate(Routes.MODS) },
                    onMarket = { nav.navigate(Routes.MARKET) },
                    onLongTail = { nav.navigate(Routes.LONGTAIL) },
                    onLogout = {
                        val dest = if (setupComplete) Routes.AUTH else Routes.CONNECT
                        vm.logout {
                            nav.navigate(dest) { popUpTo(0) { inclusive = true } }
                        }
                    },
                )
            }
            composable(Routes.CHAT) {
                ChatScreen(
                    vm,
                    onOpenWorkbench = { nav.navigate(Routes.WORKBENCH) },
                    onOpenMod = { id ->
                        vm.requestModOpen(
                            id,
                            onCloud = { nav.navigate(Routes.WORKBENCH) },
                            onNative = { nav.navigate("mod/$id") },
                        )
                    },
                )
            }
            composable(Routes.APPROVAL) {
                EnterpriseListScreen(
                    title = "审批",
                    vm = vm,
                    load = vm::loadApprovals,
                    onItemClick = { id -> nav.navigate("approval/$id") },
                )
            }
            composable(Routes.APPROVAL_DETAIL, arguments = listOf(navArgument("id") { type = NavType.IntType })) { e ->
                ApprovalDetailScreen(vm, e.arguments?.getInt("id") ?: 0) { nav.popBackStack() }
            }
            composable(Routes.ERP) { ErpScreen(vm) }
            composable(Routes.BRIDGE) { BridgeScreen(vm) }
            composable(Routes.MARKET) { ListScreen("MODstore", vm, vm::loadMarket, null) }
            composable(Routes.MODS) {
                ListScreen("Mod", vm, vm::loadMods) { id -> nav.navigate("mod/$id") }
            }
            composable(Routes.MOD_WEB, arguments = listOf(navArgument("modId") { type = NavType.StringType })) { e ->
                val modId = e.arguments?.getString("modId") ?: ""
                var bearer by remember { mutableStateOf("") }
                var url by remember { mutableStateOf("") }
                val access by vm.marketAccess.collectAsState()
                val refresh by vm.marketRefresh.collectAsState()
                LaunchedEffect(modId) {
                    bearer = vm.bearerToken()
                    url = vm.modUrl(modId)
                }
                if (url.isNotBlank()) {
                    ModWebViewScreen(url, bearer, access, refresh)
                }
            }
            composable(Routes.LONGTAIL) { LongTailScreen(vm) }
            composable(Routes.ABOUT) { AboutScreen { nav.popBackStack() } }
        }
    }
}

@Composable
fun RegisterScreen(vm: AppViewModel, onBack: () -> Unit) {
    var u by remember { mutableStateOf("") }
    var p by remember { mutableStateOf("") }
    var e by remember { mutableStateOf("") }
    Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Text("注册")
        OutlinedTextField(u, { u = it }, Modifier.fillMaxWidth(), label = { Text("用户名") })
        OutlinedTextField(p, { p = it }, Modifier.fillMaxWidth(), label = { Text("密码") })
        OutlinedTextField(e, { e = it }, Modifier.fillMaxWidth(), label = { Text("邮箱") })
        Button({ vm.register(u, p, e) { if (it) onBack() } }, Modifier.fillMaxWidth()) { Text("提交") }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ListScreen(
    title: String,
    vm: AppViewModel,
    load: () -> Unit,
    onClick: ((String) -> Unit)?,
) {
    val items by vm.items.collectAsState()
    LaunchedEffect(Unit) { load() }
    Column(Modifier.fillMaxSize()) {
        TopAppBar(title = { Text(title) })
        LazyColumn(Modifier.padding(12.dp)) {
            items(items) { item ->
                Card(
                    Modifier.fillMaxWidth().padding(vertical = 4.dp).then(
                        if (onClick != null) Modifier.clickable { onClick(item.id) } else Modifier,
                    ),
                ) {
                    Column(Modifier.padding(12.dp)) {
                        Text(item.title, style = MaterialTheme.typography.titleMedium)
                        if (item.subtitle.isNotBlank()) Text(item.subtitle)
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ApprovalDetailScreen(vm: AppViewModel, id: Int, onBack: () -> Unit) {
    val detail by vm.detailJson.collectAsState()
    var opinion by remember { mutableStateOf("") }
    LaunchedEffect(id) { vm.loadApprovalDetail(id) }
    Column(Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("审批 #$id") },
            navigationIcon = { IconButton(onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, null) } },
        )
        Text(detail, Modifier.padding(12.dp).weight(1f))
        OutlinedTextField(opinion, { opinion = it }, Modifier.fillMaxWidth().padding(12.dp), label = { Text("意见") })
        Row(Modifier.padding(12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Button({ vm.approve(id, opinion, onBack) }, Modifier.weight(1f)) { Text("通过") }
            Button({ vm.reject(id, opinion, onBack) }, Modifier.weight(1f)) { Text("驳回") }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BridgeScreen(vm: AppViewModel) {
    val items by vm.items.collectAsState()
    var reply by remember { mutableStateOf("") }
    var selectedId by remember { mutableStateOf(0) }
    LaunchedEffect(Unit) { vm.loadBridge() }
    Column(Modifier.fillMaxSize()) {
        TopAppBar(title = { Text("Service Bridge") })
        LazyColumn(Modifier.weight(1f).padding(12.dp)) {
            items(items) { item ->
                Card(Modifier.fillMaxWidth().padding(4.dp).clickable { selectedId = item.id.toIntOrNull() ?: 0 }) {
                    Text("${item.title} [${item.subtitle}]", Modifier.padding(12.dp))
                }
            }
        }
        OutlinedTextField(reply, { reply = it }, Modifier.fillMaxWidth().padding(12.dp), label = { Text("回复") })
        Button(
            {
                if (selectedId > 0 && reply.isNotBlank()) {
                    vm.bridgeRespond(selectedId, reply) { vm.loadBridge() }
                }
            },
            Modifier.padding(12.dp),
        ) { Text("回复 #$selectedId") }
    }
}

@Composable
fun LongTailScreen(vm: AppViewModel) {
    val detail by vm.detailJson.collectAsState()
    LaunchedEffect(Unit) { vm.loadFinance() }
    Column(Modifier.padding(20.dp)) {
        Text("财务摘要", style = MaterialTheme.typography.titleLarge)
        Text(detail)
        Spacer(Modifier.height(16.dp))
        Text("标签打印 / 工作流可视化请在 PC 端操作。", style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
fun OcrScreen() {
    Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text("OCR / 拍照识别", style = MaterialTheme.typography.titleLarge)
        Text(
            "请在已连接电脑的局域网模式下，通过电脑端 FHD 使用完整 OCR 与批量识别；手机端将在后续版本接入相机上传。",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Text(
            "工作台内部分 Mod 已支持图片上传与识别，可直接在工作台使用。",
            style = MaterialTheme.typography.bodySmall,
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AboutScreen(onBack: () -> Unit) {
    Column(Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("关于") },
            navigationIcon = { IconButton(onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, null) } },
        )
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(stringResource(R.string.company_name), style = MaterialTheme.typography.titleLarge)
            Text(stringResource(R.string.company_icp))
            Text(stringResource(R.string.brand_url))
        }
    }
}
