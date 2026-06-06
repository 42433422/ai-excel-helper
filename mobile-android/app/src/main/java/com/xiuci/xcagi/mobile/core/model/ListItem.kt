package com.xiuci.xcagi.mobile.core.model

data class ListItem(
    val id: String,
    val title: String,
    val subtitle: String = "",
    val payload: Map<String, Any?> = emptyMap(),
)
