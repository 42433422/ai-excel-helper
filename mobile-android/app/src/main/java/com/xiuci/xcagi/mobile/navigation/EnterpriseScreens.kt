package com.xiuci.xcagi.mobile.navigation

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.xiuci.xcagi.mobile.core.model.ListItem
import com.xiuci.xcagi.mobile.ui.AppViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EnterpriseListScreen(
    title: String,
    vm: AppViewModel,
    load: () -> Unit,
    onItemClick: ((String) -> Unit)? = null,
) {
    val items by vm.items.collectAsState()
    val loading by vm.listLoading.collectAsState()
    val error by vm.listError.collectAsState()

    LaunchedEffect(title) { load() }

    EnterpriseScaffold(
        title = title,
        onRefresh = load,
        loading = loading,
        error = error,
        isEmpty = items.isEmpty(),
        onRetry = load,
    ) {
        LazyColumn(
            contentPadding = PaddingValues(12.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            items(items) { item ->
                EnterpriseListCard(item, onItemClick)
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ErpScreen(vm: AppViewModel) {
    var tab by remember { mutableIntStateOf(0) }
    val titles = listOf("客户", "发货", "库存")
    val title = titles[tab]

    fun reload() {
        when (tab) {
            0 -> vm.loadCustomers()
            1 -> vm.loadShipments()
            else -> vm.loadInventory()
        }
    }

    LaunchedEffect(tab) { reload() }

    val items by vm.items.collectAsState()
    val loading by vm.listLoading.collectAsState()
    val error by vm.listError.collectAsState()

    Scaffold(
        topBar = {
            Column {
                TopAppBar(
                    title = { Text("业务") },
                    actions = {
                        IconButton(onClick = { reload() }) {
                            Icon(Icons.Default.Refresh, contentDescription = "刷新")
                        }
                    },
                )
                TabRow(selectedTabIndex = tab) {
                    titles.forEachIndexed { index, label ->
                        Tab(
                            selected = tab == index,
                            onClick = { tab = index },
                            text = { Text(label) },
                        )
                    }
                }
            }
        },
    ) { padding ->
        Box(
            Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
            when {
                loading && items.isEmpty() -> ListSkeleton()
                error != null && items.isEmpty() -> ListErrorState(error!!, ::reload)
                items.isEmpty() && !loading -> ListEmptyState(title, ::reload)
                else -> LazyColumn(
                    contentPadding = PaddingValues(12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(items) { item ->
                        EnterpriseListCard(item, null)
                    }
                }
            }
            if (loading && items.isNotEmpty()) {
                CircularProgressIndicator(
                    Modifier
                        .align(Alignment.TopCenter)
                        .padding(8.dp),
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun EnterpriseScaffold(
    title: String,
    onRefresh: () -> Unit,
    loading: Boolean,
    error: String?,
    isEmpty: Boolean,
    onRetry: () -> Unit,
    content: @Composable () -> Unit,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(title) },
                actions = {
                    IconButton(onClick = onRefresh) {
                        Icon(Icons.Default.Refresh, contentDescription = "刷新")
                    }
                },
            )
        },
    ) { padding ->
        Box(
            Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
            when {
                loading && isEmpty -> ListSkeleton()
                error != null && isEmpty -> ListErrorState(error, onRetry)
                isEmpty && !loading -> ListEmptyState(title, onRetry)
                else -> content()
            }
            if (loading && !isEmpty) {
                CircularProgressIndicator(
                    Modifier
                        .align(Alignment.TopCenter)
                        .padding(8.dp),
                )
            }
        }
    }
}

@Composable
private fun EnterpriseListCard(item: ListItem, onClick: ((String) -> Unit)?) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .then(
                if (onClick != null) Modifier.clickable { onClick(item.id) } else Modifier,
            ),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
    ) {
        Column(Modifier.padding(14.dp)) {
            Text(item.title, style = MaterialTheme.typography.titleMedium)
            if (item.subtitle.isNotBlank()) {
                Text(
                    item.subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
        }
    }
}

@Composable
private fun ListSkeleton() {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(12.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        items(6) {
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(12.dp),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
                ),
            ) {
                Column(Modifier.padding(14.dp)) {
                    Box(
                        Modifier
                            .fillMaxWidth(0.55f)
                            .height(14.dp)
                            .padding(bottom = 8.dp),
                    )
                    Box(
                        Modifier
                            .fillMaxWidth(0.35f)
                            .height(12.dp),
                    )
                }
            }
        }
    }
}

@Composable
private fun ListEmptyState(title: String, onRetry: () -> Unit) {
    Column(
        Modifier
            .fillMaxSize()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text("暂无${title}数据", style = MaterialTheme.typography.titleMedium)
        Text(
            "下拉刷新或连接电脑后重试。",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 8.dp, bottom = 16.dp),
        )
        Button(onClick = onRetry) { Text("刷新") }
    }
}

@Composable
private fun ListErrorState(message: String, onRetry: () -> Unit) {
    Column(
        Modifier
            .fillMaxSize()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text("加载失败", style = MaterialTheme.typography.titleMedium)
        Text(
            message,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.error,
            textAlign = TextAlign.Center,
            modifier = Modifier.padding(top = 8.dp, bottom = 16.dp),
        )
        Button(onClick = onRetry) { Text("重试") }
    }
}
