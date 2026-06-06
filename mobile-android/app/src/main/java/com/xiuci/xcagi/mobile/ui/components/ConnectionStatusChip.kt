package com.xiuci.xcagi.mobile.ui.components

import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier

@Composable
fun ConnectionStatusChip(
    label: String,
    isCloud: Boolean,
    modifier: Modifier = Modifier,
) {
    AssistChip(
        onClick = {},
        modifier = modifier,
        enabled = false,
        label = { Text(label, style = MaterialTheme.typography.labelSmall) },
        colors = AssistChipDefaults.assistChipColors(
            disabledContainerColor = if (isCloud) {
                MaterialTheme.colorScheme.primaryContainer
            } else {
                MaterialTheme.colorScheme.secondaryContainer
            },
            disabledLabelColor = if (isCloud) {
                MaterialTheme.colorScheme.onPrimaryContainer
            } else {
                MaterialTheme.colorScheme.onSecondaryContainer
            },
        ),
    )
}
