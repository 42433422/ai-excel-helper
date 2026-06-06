package com.xiuci.xcagi.mobile.feature.legal

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.xiuci.xcagi.mobile.ui.AppViewModel

@Composable
fun LegalConsentScreen(
    vm: AppViewModel,
    onAccepted: () -> Unit,
    onAbout: () -> Unit,
) {
    val config by vm.appConfig.collectAsState()
    var checked by remember { mutableStateOf(false) }
    val ctx = LocalContext.current

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text("欢迎使用 XCAGI", style = MaterialTheme.typography.headlineSmall)
        Text(
            "请阅读并同意《用户协议》和《隐私政策》后使用本应用。我们仅在为提供工作台、对话与同步服务所必需的范围内处理您的信息。",
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        OutlinedButton(
            onClick = {
                val url = config?.privacy_url?.takeIf { it.isNotBlank() }
                    ?: "https://xiu-ci.com/legal/privacy"
                ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            },
            modifier = Modifier.fillMaxWidth(),
        ) { Text("查看隐私政策") }
        OutlinedButton(
            onClick = {
                val url = config?.terms_url?.takeIf { it.isNotBlank() }
                    ?: "https://xiu-ci.com/legal/terms"
                ctx.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            },
            modifier = Modifier.fillMaxWidth(),
        ) { Text("查看用户协议") }
        RowAccept(checked) { checked = it }
        Button(
            onClick = { vm.acceptLegal(onAccepted) },
            enabled = checked,
            modifier = Modifier.fillMaxWidth(),
        ) { Text("同意并继续") }
        OutlinedButton(onAbout, Modifier.fillMaxWidth()) { Text("关于") }
    }
}

@Composable
private fun RowAccept(checked: Boolean, onChecked: (Boolean) -> Unit) {
    androidx.compose.foundation.layout.Row(
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Checkbox(checked, onCheckedChange = onChecked)
        Text("我已阅读并同意用户协议与隐私政策", style = MaterialTheme.typography.bodySmall)
    }
}
