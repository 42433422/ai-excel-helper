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
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material3.Card
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ListItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
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
import androidx.compose.ui.unit.dp
import com.xiuci.xcagi.mobile.BuildConfig
import com.xiuci.xcagi.mobile.R
import com.xiuci.xcagi.mobile.core.ProductSkuConfig
import com.xiuci.xcagi.mobile.ui.AppViewModel

@Composable
fun ProfileScreen(
    vm: AppViewModel,
    onConnectPc: () -> Unit,
    onAbout: () -> Unit,
    onSettings: () -> Unit,
    onBridge: () -> Unit,
    onMods: () -> Unit,
    onMarket: () -> Unit,
    onLongTail: () -> Unit,
    onLogout: () -> Unit,
) {
    val displayName by vm.displayName.collectAsState()
    val serverModeLabel by vm.serverModeLabel.collectAsState()
    val fhdHost by vm.fhdHost.collectAsState()
    val autoProbe by vm.autoLanProbe.collectAsState()
    val autoSync by vm.autoSync.collectAsState()
    val hub by vm.homeHub.collectAsState()
    var advancedOpen by remember { mutableStateOf(false) }
    var showDelete by remember { mutableStateOf(false) }
    var deletePassword by remember { mutableStateOf("") }

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 20.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Row(
            Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Icon(
                painter = painterResource(R.mipmap.ic_launcher),
                contentDescription = null,
                modifier = Modifier.size(56.dp),
                tint = Color.Unspecified,
            )
            Column {
                Text(stringResource(R.string.app_name), style = MaterialTheme.typography.titleLarge)
                Text(
                    displayName.ifBlank { "未登录" },
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    serverModeLabel,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }

        Card(Modifier.fillMaxWidth()) {
            ListItem(
                headlineContent = { Text("连接电脑") },
                supportingContent = {
                    Text(
                        if (fhdHost.isBlank()) "未配置，可使用云端工作台" else "当前：$fhdHost",
                        style = MaterialTheme.typography.bodySmall,
                    )
                },
            )
            HorizontalDivider()
            TextButton(onClick = onConnectPc, modifier = Modifier.fillMaxWidth()) {
                Text("连接 / 更换电脑")
            }
        }

        Card(Modifier.fillMaxWidth()) {
            ListItem(
                headlineContent = { Text("后台自动发现电脑") },
                trailingContent = {
                    Switch(autoProbe, { vm.setAutoLanProbe(it) })
                },
            )
            Text(
                "关闭后不在后台扫描局域网。",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(start = 16.dp, end = 16.dp, bottom = 8.dp),
            )
            HorizontalDivider()
            ListItem(
                headlineContent = { Text("后台自动同步") },
                supportingContent = { Text(hub.syncLabel) },
                trailingContent = {
                    Switch(autoSync, { vm.setAutoSync(it) })
                },
            )
            TextButton(
                onClick = { vm.runSyncNow() },
                modifier = Modifier.fillMaxWidth(),
                enabled = !hub.syncing,
            ) {
                Text(if (hub.syncing) "同步中…" else "立即同步工作数据")
            }
        }

        Card(Modifier.fillMaxWidth()) {
            ListItem(
                headlineContent = { Text("设置") },
                modifier = Modifier.clickable(onClick = onSettings),
            )
            HorizontalDivider()
            ListItem(
                headlineContent = { Text("关于") },
                supportingContent = { Text(stringResource(R.string.company_name)) },
                modifier = Modifier.clickable(onClick = onAbout),
            )
            HorizontalDivider()
            ListItem(
                headlineContent = { Text("版本") },
                supportingContent = { Text("${BuildConfig.VERSION_NAME} (${BuildConfig.VERSION_CODE})") },
            )
        }

        Row(
            Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("高级", style = MaterialTheme.typography.titleSmall)
            Spacer(Modifier.weight(1f))
            IconButton({ advancedOpen = !advancedOpen }) {
                Icon(
                    if (advancedOpen) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                    contentDescription = null,
                )
            }
        }

        if (advancedOpen) {
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(8.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    ProfileNavRow("Service Bridge", onBridge)
                    ProfileNavRow("Mod 列表", onMods)
                    ProfileNavRow("插件市场", onMarket)
                    if (ProductSkuConfig.showsEnterpriseNav) {
                        ProfileNavRow("财务 / 打印摘要", onLongTail)
                    }
                }
            }
        }

        Spacer(Modifier.height(8.dp))

        OutlinedButton(onClick = onLogout, modifier = Modifier.fillMaxWidth()) {
            Text("退出登录")
        }
        TextButton(
            onClick = { showDelete = true },
            modifier = Modifier.fillMaxWidth(),
        ) {
            Text("注销账号", color = MaterialTheme.colorScheme.error)
        }
    }

    if (showDelete) {
        androidx.compose.material3.AlertDialog(
            onDismissRequest = { showDelete = false },
            title = { Text("注销账号") },
            text = {
                Column {
                    Text("注销后无法恢复，请确认密码。")
                    OutlinedTextField(
                        deletePassword,
                        { deletePassword = it },
                        label = { Text("密码") },
                    )
                }
            },
            confirmButton = {
                TextButton({
                    vm.deleteAccount(deletePassword) {
                        showDelete = false
                        onLogout()
                    }
                }) { Text("确认注销") }
            },
            dismissButton = {
                TextButton({ showDelete = false }) { Text("取消") }
            },
        )
    }
}

@Composable
private fun ProfileNavRow(label: String, onClick: () -> Unit) {
    ListItem(
        headlineContent = { Text(label) },
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick),
    )
}
