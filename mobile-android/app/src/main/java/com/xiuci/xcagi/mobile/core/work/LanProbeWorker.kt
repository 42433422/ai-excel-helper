package com.xiuci.xcagi.mobile.core.work

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.xiuci.xcagi.mobile.core.datastore.SessionStore
import com.xiuci.xcagi.mobile.core.network.LanScanner
import com.xiuci.xcagi.mobile.core.network.ServerMode
import com.xiuci.xcagi.mobile.core.network.ServerRouter
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.coroutines.flow.first

@HiltWorker
class LanProbeWorker @AssistedInject constructor(
    @Assisted ctx: Context,
    @Assisted params: WorkerParameters,
    private val sessionStore: SessionStore,
    private val serverRouter: ServerRouter,
    private val lanScanner: LanScanner,
) : CoroutineWorker(ctx, params) {

    override suspend fun doWork(): Result {
        val host = sessionStore.fhdHostFlow.first().ifBlank { return Result.success() }
        val bare = host.substringBefore(':').trim()
        val ok = lanScanner.probeHealth(bare)
        if (!ok && serverRouter.mode == ServerMode.LAN) {
            sessionStore.setServerMode("cloud")
            serverRouter.mode = ServerMode.CLOUD
        } else if (ok && sessionStore.serverModeFlow.first() == "cloud") {
            sessionStore.setServerMode("lan")
            serverRouter.mode = ServerMode.LAN
        }
        return Result.success()
    }
}
