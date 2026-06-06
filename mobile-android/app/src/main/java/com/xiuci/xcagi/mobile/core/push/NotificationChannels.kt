package com.xiuci.xcagi.mobile.core.push

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import androidx.core.app.NotificationManagerCompat

object NotificationChannels {
    const val APPROVAL = "xcagi_approval"
    const val SYNC = "xcagi_sync"
    const val SYSTEM = "xcagi_system"
    const val CHAT = "xcagi_chat"

    fun ensure(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return
        val mgr = context.getSystemService(NotificationManager::class.java) ?: return
        listOf(
            Triple(APPROVAL, "审批通知", NotificationManager.IMPORTANCE_HIGH),
            Triple(SYNC, "同步", NotificationManager.IMPORTANCE_LOW),
            Triple(SYSTEM, "系统", NotificationManager.IMPORTANCE_DEFAULT),
            Triple(CHAT, "对话", NotificationManager.IMPORTANCE_DEFAULT),
        ).forEach { (id, name, imp) ->
            mgr.createNotificationChannel(
                NotificationChannel(id, name, imp).apply {
                    description = "XCAGI $name"
                },
            )
        }
        NotificationManagerCompat.from(context).areNotificationsEnabled()
    }
}
