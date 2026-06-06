package com.xiuci.xcagi.mobile.feature.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.xiuci.xcagi.mobile.ui.AppViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(vm: AppViewModel, onBack: () -> Unit) {
    val biometric by vm.biometricEnabled.collectAsState()
    val themeMode by vm.themeMode.collectAsState()
    var feedback by remember { mutableStateOf("") }

    Column(Modifier.fillMaxSize()) {
        TopAppBar(
            title = { Text("设置") },
            navigationIcon = {
                IconButton(onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "返回")
                }
            },
        )
        Column(
            Modifier
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text("安全", style = MaterialTheme.typography.titleMedium)
            androidx.compose.foundation.layout.Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text("指纹/面容解锁")
                Switch(biometric, onCheckedChange = { vm.setBiometricEnabled(it) })
            }
            Text("外观", style = MaterialTheme.typography.titleMedium)
            Text("主题：$themeMode", style = MaterialTheme.typography.bodyMedium)
            androidx.compose.foundation.layout.Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                androidx.compose.material3.OutlinedButton({ vm.setThemeMode("system") }) { Text("跟随系统") }
                androidx.compose.material3.OutlinedButton({ vm.setThemeMode("dark") }) { Text("深色") }
                androidx.compose.material3.OutlinedButton({ vm.setThemeMode("light") }) { Text("浅色") }
            }
            Text("反馈", style = MaterialTheme.typography.titleMedium)
            OutlinedTextField(
                feedback,
                { feedback = it },
                Modifier.fillMaxWidth(),
                label = { Text("问题描述") },
                minLines = 3,
            )
            androidx.compose.material3.Button(
                { vm.submitFeedback(feedback) { feedback = "" } },
                Modifier.fillMaxWidth(),
                enabled = feedback.isNotBlank(),
            ) { Text("提交反馈") }
            androidx.compose.material3.OutlinedButton(
                { vm.checkForUpdate(manual = true) },
                Modifier.fillMaxWidth(),
            ) { Text("检查更新") }
        }
    }
}
