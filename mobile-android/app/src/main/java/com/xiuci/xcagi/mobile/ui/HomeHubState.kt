package com.xiuci.xcagi.mobile.ui

import com.xiuci.xcagi.mobile.core.model.ListItem

data class HomeHubState(
    val loading: Boolean = true,
    val pcOnline: Boolean = false,
    val mods: List<ListItem> = emptyList(),
    val modsFromCloud: Boolean = false,
    val syncLabel: String = "尚未同步",
    val syncing: Boolean = false,
)

data class ChatSuggestion(
    val label: String,
    val prompt: String,
)
