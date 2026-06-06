package com.xiuci.xcagi.mobile.core.work

import android.content.Context
import androidx.hilt.work.HiltWorker
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import com.xiuci.xcagi.mobile.core.datastore.SessionStore
import com.xiuci.xcagi.mobile.core.sync.MobileSyncRepository
import dagger.assisted.Assisted
import dagger.assisted.AssistedInject
import kotlinx.coroutines.flow.first

@HiltWorker
class MobileSyncWorker @AssistedInject constructor(
    @Assisted ctx: Context,
    @Assisted params: WorkerParameters,
    private val sessionStore: SessionStore,
    private val syncRepo: MobileSyncRepository,
) : CoroutineWorker(ctx, params) {

    override suspend fun doWork(): Result {
        if (!sessionStore.autoSyncFlow.first()) return Result.success()
        val host = sessionStore.fhdHostFlow.first()
        if (host.isBlank()) return Result.success()
        return syncRepo.pullAndCache().fold(
            onSuccess = { Result.success() },
            onFailure = { Result.retry() },
        )
    }
}
