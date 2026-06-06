package com.xiuci.xcagi.mobile.core.sync

import com.google.gson.Gson
import com.xiuci.xcagi.mobile.core.datastore.SessionStore
import com.xiuci.xcagi.mobile.core.db.ApprovalCacheEntity
import com.xiuci.xcagi.mobile.core.db.ShipmentCacheEntity
import com.xiuci.xcagi.mobile.core.db.XcagiDatabase
import com.xiuci.xcagi.mobile.core.network.FhdApi
import com.xiuci.xcagi.mobile.core.network.ServerRouter
import com.xiuci.xcagi.mobile.core.network.SyncPullBody
import com.xiuci.xcagi.mobile.core.repository.XcagiRepository
import kotlinx.coroutines.flow.first
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.time.Instant
import javax.inject.Inject
import javax.inject.Singleton

data class SyncStatusSummary(
    val label: String,
    val healthy: Boolean = false,
    val cursor: Int = 0,
    val lastSyncAt: String = "",
)

@Singleton
class MobileSyncRepository @Inject constructor(
    private val sessionStore: SessionStore,
    private val serverRouter: ServerRouter,
    private val repo: XcagiRepository,
    private val db: XcagiDatabase,
    private val okHttp: okhttp3.OkHttpClient,
    private val gson: Gson = Gson(),
) {
    private var fhdApi: FhdApi? = null
    private var cachedBase: String = ""

    private suspend fun fhd(): FhdApi {
        repo.syncRouterFromStore()
        val base = serverRouter.fhdBaseUrl()
        if (fhdApi == null || cachedBase != base) {
            cachedBase = base
            fhdApi = Retrofit.Builder().baseUrl(base)
                .client(okHttp)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(FhdApi::class.java)
        }
        return fhdApi!!
    }

    suspend fun fetchRemoteStatus(): Result<Map<String, Any?>> = try {
        repo.syncRouterFromStore()
        val res = fhd().mobileSyncStatus()
        if (!res.success) Result.failure(Exception(res.message ?: "sync status failed"))
        else Result.success(res.data ?: emptyMap())
    } catch (e: Exception) {
        Result.failure(e)
    }

    suspend fun pullAndCache(): Result<SyncStatusSummary> {
        return try {
            repo.syncRouterFromStore()
            if (!repo.checkHealth()) {
                return Result.failure(Exception("电脑未在线"))
            }
            val since = sessionStore.syncCursor()
            val res = fhd().mobileSyncPull(SyncPullBody(since))
            if (!res.success) {
                return Result.failure(Exception(res.message ?: "同步失败"))
            }
            val data = res.data ?: emptyMap()
            val cursor = (data["cursor"] as? Number)?.toInt() ?: since
            sessionStore.setSyncCursor(cursor)
            val now = Instant.now().toString()
            sessionStore.setLastSyncAt(now)

            @Suppress("UNCHECKED_CAST")
            val approvals = (data["approvals"] as? List<Map<String, Any?>>) ?: emptyList()
            approvals.forEach { row ->
                val id = (row["id"] as? Number)?.toInt() ?: return@forEach
                db.approvalDao().insert(
                    ApprovalCacheEntity(
                        requestId = id,
                        title = row["title"]?.toString() ?: "",
                        status = row["status"]?.toString() ?: "",
                        json = gson.toJson(row),
                    ),
                )
            }

            @Suppress("UNCHECKED_CAST")
            val shipments = (data["shipments"] as? List<Map<String, Any?>>) ?: emptyList()
            shipments.forEach { row ->
                val id = (row["id"] as? Number)?.toInt() ?: return@forEach
                db.shipmentDao().insert(
                    ShipmentCacheEntity(
                        shipmentId = id,
                        orderNumber = row["order_number"]?.toString() ?: "",
                        status = row["status"]?.toString() ?: "",
                        json = gson.toJson(row),
                    ),
                )
            }

            Result.success(
                SyncStatusSummary(
                    label = "已同步",
                    healthy = true,
                    cursor = cursor,
                    lastSyncAt = now,
                ),
            )
        } catch (e: Exception) {
            Result.failure(e)
        }
    }

    suspend fun statusLabel(pcOnline: Boolean): String {
        val last = sessionStore.lastSyncAtFlow.first()
        return when {
            !pcOnline -> "需连接电脑"
            last.isBlank() -> "尚未同步"
            else -> "上次同步 ${last.take(19).replace('T', ' ')}"
        }
    }
}
