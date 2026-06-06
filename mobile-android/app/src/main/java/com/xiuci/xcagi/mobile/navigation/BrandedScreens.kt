package com.xiuci.xcagi.mobile.navigation

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.xiuci.xcagi.mobile.R
import com.xiuci.xcagi.mobile.core.ProductSkuConfig
import com.xiuci.xcagi.mobile.ui.AppViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConnectScreen(
    vm: AppViewModel,
    fromProfile: Boolean,
    onNext: () -> Unit,
    onScan: () -> Unit,
    onSkipCloud: () -> Unit,
    onBack: (() -> Unit)? = null,
) {
    val loggedIn by vm.isLoggedIn.collectAsState()
    var pcExpanded by remember { mutableStateOf(fromProfile) }
    var host by remember { mutableStateOf("192.168.1.100") }
    var prefix by remember { mutableStateOf("192.168.1") }
    var cloud by remember { mutableStateOf(true) }
    val scans by vm.scanResults.collectAsState()
    val savedHost by vm.fhdHost.collectAsState()

    LaunchedEffect(savedHost) {
        if (savedHost.isNotBlank()) host = savedHost.substringBefore(':').ifBlank { savedHost }
    }

    Column(Modifier.fillMaxSize()) {
        if (fromProfile || loggedIn) {
            TopAppBar(
                title = { Text("连接电脑") },
                navigationIcon = {
                    IconButton(onClick = { onBack?.invoke() }) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "返回")
                    }
                },
            )
        }

        Column(
            Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            if (!fromProfile && !loggedIn) {
                Column(
                    Modifier.fillMaxWidth(),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Icon(
                        painter = painterResource(R.mipmap.ic_launcher),
                        contentDescription = null,
                        modifier = Modifier.size(72.dp),
                        tint = Color.Unspecified,
                    )
                    Spacer(Modifier.height(12.dp))
                    Text(stringResource(R.string.app_name), style = MaterialTheme.typography.headlineMedium)
                    Text(
                        "独立客户端，可与电脑协同，也可直接使用云端。",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.padding(top = 8.dp),
                    )
                }
                Spacer(Modifier.height(8.dp))
                Button(onSkipCloud, Modifier.fillMaxWidth()) { Text("进入云端使用") }
                OutlinedButton({ pcExpanded = !pcExpanded }, Modifier.fillMaxWidth()) {
                    Text(if (pcExpanded) "收起电脑连接" else "连接电脑（可选）")
                }
            }

            if (fromProfile || loggedIn || pcExpanded) {
                Text("连接电脑", style = MaterialTheme.typography.titleMedium)
                OutlinedTextField(host, { host = it }, Modifier.fillMaxWidth(), label = { Text("电脑 IP") })
                OutlinedTextField(prefix, { prefix = it }, Modifier.fillMaxWidth(), label = { Text("扫描网段前缀") })
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("云端模式")
                    Switch(cloud, { cloud = it; vm.setMode(it) })
                }
                Button(
                    {
                        vm.setHost(host)
                        vm.probeHealth(host) {
                            if (it) {
                                vm.setHost(host, markSetup = true)
                                if (fromProfile || loggedIn) onBack?.invoke() else onNext()
                            } else {
                                vm.snack("无法连接", true)
                            }
                        }
                    },
                    Modifier.fillMaxWidth(),
                ) { Text("检测并保存") }
                OutlinedButton({ vm.scanSubnet(prefix) }, Modifier.fillMaxWidth()) { Text("扫描局域网") }
                scans.forEach { ip ->
                    Text(ip, Modifier.clickable { host = ip; vm.setHost(ip) })
                }
                OutlinedButton(onScan, Modifier.fillMaxWidth()) { Text("扫码配对") }
                OutlinedButton({ vm.lanRequest("Android") }, Modifier.fillMaxWidth()) { Text("入网申请") }
                if (!fromProfile && !loggedIn && cloud) {
                    Button(onNext, Modifier.fillMaxWidth()) { Text("使用云端并登录") }
                }
            }
        }
    }
}

@Composable
fun AuthScreen(vm: AppViewModel, onRegister: () -> Unit, onDone: () -> Unit) {
    var tab by remember { mutableStateOf(if (ProductSkuConfig.isEnterprise) 1 else 0) }
    var user by remember { mutableStateOf("") }
    var pass by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }
    var code by remember { mutableStateOf("") }
    val accountLabel = if (ProductSkuConfig.isEnterprise) "企业账号" else "账号密码"

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Icon(
            painter = painterResource(R.mipmap.ic_launcher),
            contentDescription = null,
            modifier = Modifier.size(80.dp),
            tint = Color.Unspecified,
        )
        Text(
            if (ProductSkuConfig.isEnterprise) "XCAGI 企业版" else "XCAGI 个人版",
            style = MaterialTheme.typography.headlineSmall,
        )
        Text(
            stringResource(R.string.company_name),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        Text(
            "无需电脑即可使用；与官网 MODstore 同一账号，登录后工作台与云端能力直接可用。",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(horizontal = 8.dp),
        )
        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton({ tab = 0 }, Modifier.weight(1f), enabled = tab != 0) {
                        Text(accountLabel, maxLines = 1)
                    }
                    OutlinedButton({ tab = 1 }, Modifier.weight(1f), enabled = tab != 1) {
                        Text("手机号", maxLines = 1)
                    }
                }
                if (tab == 0) {
                    OutlinedTextField(user, { user = it }, Modifier.fillMaxWidth(), label = { Text("用户名") })
                    OutlinedTextField(pass, { pass = it }, Modifier.fillMaxWidth(), label = { Text("密码") })
                    Text(
                        "默认直连云端；仅当已连接电脑且电脑在线时，才走电脑端会话。",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Button({ vm.loginFhd(user, pass) { if (it) onDone() } }, Modifier.fillMaxWidth()) {
                        Text("登录")
                    }
                    if (!ProductSkuConfig.isEnterprise) {
                        OutlinedButton(onRegister, Modifier.fillMaxWidth()) { Text("注册账号") }
                    }
                } else {
                    OutlinedTextField(phone, { phone = it }, Modifier.fillMaxWidth(), label = { Text("手机号") })
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(code, { code = it }, Modifier.weight(1f), label = { Text("验证码") })
                        Button({ vm.sendCode(phone) }) { Text("发送") }
                    }
                    Button({ vm.loginPhone(phone, code) { if (it) onDone() } }, Modifier.fillMaxWidth()) {
                        Text("登录")
                    }
                }
            }
        }
    }
}
