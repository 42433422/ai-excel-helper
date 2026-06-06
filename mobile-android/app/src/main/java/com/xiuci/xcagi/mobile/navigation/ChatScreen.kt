package com.xiuci.xcagi.mobile.navigation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material3.Button
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
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
import androidx.compose.ui.unit.dp
import com.xiuci.xcagi.mobile.ui.AppViewModel
import com.xiuci.xcagi.mobile.ui.components.ConnectionStatusChip

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun ChatScreen(
    vm: AppViewModel,
    onOpenWorkbench: () -> Unit,
    onOpenMod: (String) -> Unit,
) {
    val messages by vm.chatMessages.collectAsState()
    val streaming by vm.streaming.collectAsState()
    val connectionChip by vm.chatConnectionChip.collectAsState()
    val isCloud by vm.isCloudMode.collectAsState()
    val suggestions by vm.chatSuggestions.collectAsState()
    val syncStale by vm.syncStaleHint.collectAsState()
    val canUseNativeChat by vm.canUseNativeChat.collectAsState()
    val chatAction by vm.chatAction.collectAsState()
    var input by remember { mutableStateOf("") }
    val listState = rememberLazyListState()

    LaunchedEffect(Unit) {
        vm.loadChatCache()
        if (suggestions.isEmpty()) vm.loadHomeHub()
    }

    LaunchedEffect(messages.size, streaming) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.lastIndex)
        }
    }

    Column(Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("AI 助手") },
            actions = {
                ConnectionStatusChip(
                    label = connectionChip,
                    isCloud = isCloud,
                    modifier = Modifier.padding(end = 12.dp),
                )
            },
        )
        if (!canUseNativeChat) {
            Text(
                "云端账号请在工作台使用 AI；连接电脑并登录电脑端账号后可使用本页原生对话。",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
            )
        }
        if (syncStale) {
            Text(
                "数据可能不是最新，请在首页执行「立即同步」。",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.tertiary,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
            )
        }
        chatAction?.let { action ->
            Row(
                Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 4.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                when (action.type) {
                    "workbench" -> Button(onClick = {
                        vm.clearChatAction()
                        onOpenWorkbench()
                    }) { Text("打开工作台") }
                    "mod" -> Button(onClick = {
                        vm.clearChatAction()
                        onOpenMod(action.targetId)
                    }) { Text("打开 ${action.label}") }
                }
            }
        }
        if (suggestions.isNotEmpty()) {
            FlowRow(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 4.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                suggestions.forEach { s ->
                    FilterChip(
                        selected = false,
                        onClick = {
                            input = s.prompt
                            vm.sendChat(s.prompt)
                        },
                        label = { Text(s.label) },
                    )
                }
            }
        }
        if (messages.isEmpty()) {
            Box(
                Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .padding(24.dp),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    "统一 AI 入口：可提问、查审批、打开 Mod 或工作台。",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        } else {
            LazyColumn(
                Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .padding(horizontal = 12.dp, vertical = 8.dp),
                state = listState,
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                items(messages) { (role, text) ->
                    ChatBubble(role = role, text = text)
                }
            }
        }
        Row(
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 12.dp, vertical = 8.dp),
            verticalAlignment = Alignment.Bottom,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            OutlinedTextField(
                value = input,
                onValueChange = { input = it },
                modifier = Modifier.weight(1f),
                placeholder = { Text("输入消息…") },
                maxLines = 4,
            )
            IconButton(
                onClick = {
                    if (streaming) {
                        vm.stopChat()
                    } else if (input.isNotBlank()) {
                        vm.sendChat(input.trim())
                        input = ""
                    }
                },
            ) {
                Icon(
                    Icons.AutoMirrored.Filled.Send,
                    contentDescription = if (streaming) "停止" else "发送",
                )
            }
        }
    }
}

@Composable
private fun ChatBubble(role: String, text: String) {
    val isUser = role == "user"
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
    ) {
        Surface(
            modifier = Modifier.widthIn(max = 320.dp),
            shape = RoundedCornerShape(
                topStart = 16.dp,
                topEnd = 16.dp,
                bottomStart = if (isUser) 16.dp else 4.dp,
                bottomEnd = if (isUser) 4.dp else 16.dp,
            ),
            color = if (isUser) {
                MaterialTheme.colorScheme.primaryContainer
            } else {
                MaterialTheme.colorScheme.surfaceVariant
            },
        ) {
            Column(Modifier.padding(horizontal = 14.dp, vertical = 10.dp)) {
                Text(
                    if (isUser) "我" else "AI",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                Text(
                    text,
                    style = MaterialTheme.typography.bodyMedium,
                    color = if (isUser) {
                        MaterialTheme.colorScheme.onPrimaryContainer
                    } else {
                        MaterialTheme.colorScheme.onSurface
                    },
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
        }
    }
}
