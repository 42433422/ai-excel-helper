package com.xiuci.xcagi.mobile.navigation

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Chat
import androidx.compose.material.icons.filled.Computer
import androidx.compose.material.icons.filled.Dashboard
import androidx.compose.material.icons.filled.Extension
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.material3.Icon
import androidx.compose.material3.ListItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.xiuci.xcagi.mobile.R
import com.xiuci.xcagi.mobile.core.model.ListItem
import com.xiuci.xcagi.mobile.ui.AppViewModel

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun HomeHubScreen(
    vm: AppViewModel,
    onChat: () -> Unit,
    onWorkbench: () -> Unit,
    onConnectPc: () -> Unit,
    onModClick: (String) -> Unit,
) {
    val hub by vm.homeHub.collectAsState()
    val serverLabel by vm.serverModeLabel.collectAsState()
    val fhdHost by vm.fhdHost.collectAsState()

    LaunchedEffect(Unit) { vm.loadHomeHub() }

    Column(Modifier.fillMaxSize()) {
        TopAppBar(title = { Text("首页") })
        PullToRefreshBox(
            isRefreshing = hub.loading,
            onRefresh = { vm.loadHomeHub() },
            modifier = Modifier.weight(1f),
        ) {
        if (hub.loading && hub.mods.isEmpty()) {
            Column(
                Modifier.fillMaxSize(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                CircularProgressIndicator()
            }
        } else {
            Column(
                Modifier
                    .fillMaxSize()
                    .verticalScroll(rememberScrollState())
                    .padding(16.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("我的电脑", style = MaterialTheme.typography.titleMedium)
                        Text(
                            if (fhdHost.isBlank()) "未连接 · 可使用云端能力" else "主机：$fhdHost",
                            style = MaterialTheme.typography.bodyMedium,
                        )
                        Text(serverLabel, style = MaterialTheme.typography.bodySmall)
                        Text(
                            if (hub.pcOnline) "电脑在线" else "电脑离线或未配置",
                            color = if (hub.pcOnline) {
                                MaterialTheme.colorScheme.primary
                            } else {
                                MaterialTheme.colorScheme.onSurfaceVariant
                            },
                        )
                        Text(hub.syncLabel, style = MaterialTheme.typography.bodySmall)
                        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedButton(onClick = onConnectPc) {
                                Icon(Icons.Default.Computer, null, Modifier.padding(end = 4.dp))
                                Text("连接电脑")
                            }
                            Button(
                                onClick = { vm.runSyncNow() },
                                enabled = hub.pcOnline && !hub.syncing,
                            ) {
                                Icon(Icons.Default.Sync, null, Modifier.padding(end = 4.dp))
                                Text(if (hub.syncing) "同步中…" else "立即同步")
                            }
                        }
                    }
                }

                Text("快捷入口", style = MaterialTheme.typography.titleSmall)
                FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = onChat) {
                        Icon(Icons.Default.Chat, null, Modifier.padding(end = 4.dp))
                        Text("AI 对话")
                    }
                    OutlinedButton(onClick = onWorkbench) {
                        Icon(Icons.Default.Dashboard, null, Modifier.padding(end = 4.dp))
                        Text("工作台")
                    }
                }

                Text(
                    if (hub.modsFromCloud) {
                        "MODstore 推荐"
                    } else {
                        stringResource(R.string.app_name) + " · 已安装 Mod"
                    },
                    style = MaterialTheme.typography.titleSmall,
                )
                if (hub.mods.isEmpty()) {
                    Text(
                        "连接电脑后可查看本机 Mod；已登录云端账号时也可在工作台浏览全部能力。",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                } else {
                    hub.mods.chunked(2).forEach { row ->
                        Row(
                            Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            row.forEach { mod ->
                                ModTile(
                                    mod,
                                    Modifier.weight(1f),
                                ) { onModClick(mod.id) }
                            }
                            if (row.size == 1) {
                                androidx.compose.foundation.layout.Spacer(Modifier.weight(1f))
                            }
                        }
                    }
                }
            }
        }
        }
    }
}

@Composable
private fun ModTile(mod: ListItem, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Card(
        modifier
            .clickable(onClick = onClick),
    ) {
        ListItem(
            headlineContent = { Text(mod.title, maxLines = 2) },
            leadingContent = { Icon(Icons.Default.Extension, contentDescription = null) },
        )
    }
}
