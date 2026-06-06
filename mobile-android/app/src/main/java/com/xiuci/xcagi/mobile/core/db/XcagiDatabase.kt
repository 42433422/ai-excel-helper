package com.xiuci.xcagi.mobile.core.db

import androidx.room.Dao
import androidx.room.Database
import androidx.room.Entity
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.PrimaryKey
import androidx.room.Query
import androidx.room.RoomDatabase

@Entity(tableName = "chat_cache")
data class ChatCacheEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val role: String,
    val text: String,
    val ts: Long = System.currentTimeMillis(),
)

@Entity(tableName = "approval_cache")
data class ApprovalCacheEntity(
    @PrimaryKey val requestId: Int,
    val title: String,
    val status: String,
    val json: String,
    val ts: Long = System.currentTimeMillis(),
)

@Dao
interface ChatCacheDao {
    @Query("SELECT * FROM chat_cache ORDER BY id ASC LIMIT 200")
    suspend fun all(): List<ChatCacheEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(row: ChatCacheEntity)

    @Query("DELETE FROM chat_cache")
    suspend fun clear()
}

@Entity(tableName = "shipment_cache")
data class ShipmentCacheEntity(
    @PrimaryKey val shipmentId: Int,
    val orderNumber: String,
    val status: String,
    val json: String,
    val ts: Long = System.currentTimeMillis(),
)

@Dao
interface ShipmentCacheDao {
    @Query("SELECT * FROM shipment_cache ORDER BY ts DESC LIMIT 100")
    suspend fun all(): List<ShipmentCacheEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(row: ShipmentCacheEntity)

    @Query("DELETE FROM shipment_cache")
    suspend fun clear()
}

@Dao
interface ApprovalCacheDao {
    @Query("SELECT * FROM approval_cache ORDER BY ts DESC LIMIT 100")
    suspend fun all(): List<ApprovalCacheEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(row: ApprovalCacheEntity)

    @Query("DELETE FROM approval_cache")
    suspend fun clear()
}

@Database(
    entities = [ChatCacheEntity::class, ApprovalCacheEntity::class, ShipmentCacheEntity::class],
    version = 2,
    exportSchema = false,
)
abstract class XcagiDatabase : RoomDatabase() {
    abstract fun chatDao(): ChatCacheDao
    abstract fun approvalDao(): ApprovalCacheDao
    abstract fun shipmentDao(): ShipmentCacheDao
}
