package com.xiuci.xcagi.mobile.core.push

import android.content.Context
import android.os.Build
import androidx.core.content.ContextCompat
import cn.jpush.android.api.JPushInterface
import com.google.firebase.messaging.FirebaseMessaging
import com.xiuci.xcagi.mobile.core.datastore.SessionStore
import com.xiuci.xcagi.mobile.core.repository.XcagiRepository
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.tasks.await
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class PushRegistrar @Inject constructor(
    @ApplicationContext private val context: Context,
    private val sessionStore: SessionStore,
    private val repo: XcagiRepository,
) {
    fun initSdk() {
        NotificationChannels.ensure(context)
        try {
            JPushInterface.setDebugMode(false)
            JPushInterface.init(context)
        } catch (_: Exception) {
        }
    }

    suspend fun registerAll() {
        initSdk()
        var fcm = PushTokenHolder.fcmToken
        if (fcm.isBlank()) {
            try {
                fcm = FirebaseMessaging.getInstance().token.await()
                PushTokenHolder.fcmToken = fcm
            } catch (_: Exception) {
            }
        }
        if (fcm.isNotBlank()) {
            sessionStore.setFcmToken(fcm)
            repo.registerDeviceToken(pushProvider = "fcm", pushToken = fcm)
        }
        try {
            val rid = JPushInterface.getRegistrationID(context)
            if (!rid.isNullOrBlank()) {
                PushTokenHolder.jpushRegistrationId = rid
                repo.registerDeviceToken(pushProvider = "jpush", pushToken = rid)
            }
        } catch (_: Exception) {
        }
    }

    fun unregisterAll() {
        try {
            JPushInterface.deleteAlias(context, 0)
        } catch (_: Exception) {
        }
    }
}
