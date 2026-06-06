package com.xiuci.xcagi.mobile.core.datastore

import android.content.Context
import com.xiuci.xcagi.mobile.BuildConfig
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore: DataStore<Preferences> by preferencesDataStore(
    "xcagi_session_${BuildConfig.PRODUCT_SKU}",
)

@Singleton
class SessionStore @Inject constructor(
    @ApplicationContext private val context: Context,
) {
    private val fhdHost = stringPreferencesKey("fhd_host")
    private val fhdAccess = stringPreferencesKey("fhd_access_token")
    private val fhdRefresh = stringPreferencesKey("fhd_refresh_token")
    private val fhdSession = stringPreferencesKey("fhd_session_id")
    private val fhdUsername = stringPreferencesKey("fhd_username")
    private val marketToken = stringPreferencesKey("market_token")
    private val marketRefresh = stringPreferencesKey("market_refresh_token")
    private val serverMode = stringPreferencesKey("server_mode")
    private val userIdKey = intPreferencesKey("user_id")
    private val fcmTokenKey = stringPreferencesKey("fcm_token")
    private val setupCompleteKey = booleanPreferencesKey("setup_complete")
    private val autoLanProbeKey = booleanPreferencesKey("auto_lan_probe")
    private val syncCursorKey = intPreferencesKey("sync_cursor")
    private val lastSyncAtKey = stringPreferencesKey("last_sync_at")
    private val autoSyncKey = booleanPreferencesKey("auto_sync")
    private val legalAcceptedVersionKey = stringPreferencesKey("legal_accepted_version")
    private val themeModeKey = stringPreferencesKey("theme_mode")
    private val biometricEnabledKey = booleanPreferencesKey("biometric_enabled")

    val fhdHostFlow: Flow<String> = context.dataStore.data.map { it[fhdHost] ?: "" }
    val userIdFlow: Flow<Int> = context.dataStore.data.map { it[userIdKey] ?: 0 }
    val fhdAccessFlow: Flow<String> = context.dataStore.data.map { it[fhdAccess] ?: "" }
    val serverModeFlow: Flow<String> = context.dataStore.data.map { it[serverMode] ?: "cloud" }
    val marketTokenFlow: Flow<String> = context.dataStore.data.map { it[marketToken] ?: "" }
    val marketRefreshFlow: Flow<String> = context.dataStore.data.map { it[marketRefresh] ?: "" }
    val fhdUsernameFlow: Flow<String> = context.dataStore.data.map { it[fhdUsername] ?: "" }

    val isLoggedInFlow: Flow<Boolean> = context.dataStore.data.map {
        !(it[fhdAccess].isNullOrBlank()) || !(it[marketToken].isNullOrBlank())
    }

    /** 已完成引导：显式标记或已保存电脑主机。 */
    val isSetupCompleteFlow: Flow<Boolean> = context.dataStore.data.map { prefs ->
        prefs[setupCompleteKey] == true || !(prefs[fhdHost].isNullOrBlank())
    }

    val autoLanProbeFlow: Flow<Boolean> = context.dataStore.data.map {
        it[autoLanProbeKey] == true
    }

    val syncCursorFlow: Flow<Int> = context.dataStore.data.map { it[syncCursorKey] ?: 0 }

    val lastSyncAtFlow: Flow<String> = context.dataStore.data.map { it[lastSyncAtKey] ?: "" }

    val autoSyncFlow: Flow<Boolean> = context.dataStore.data.map { it[autoSyncKey] != false }

    val legalAcceptedVersionFlow: Flow<String> = context.dataStore.data.map { it[legalAcceptedVersionKey] ?: "" }

    val themeModeFlow: Flow<String> = context.dataStore.data.map { it[themeModeKey] ?: "system" }

    val biometricEnabledFlow: Flow<Boolean> = context.dataStore.data.map { it[biometricEnabledKey] == true }

    suspend fun isSetupComplete(): Boolean = isSetupCompleteFlow.first()

    suspend fun setSetupComplete(complete: Boolean = true) {
        context.dataStore.edit { it[setupCompleteKey] = complete }
    }

    suspend fun setAutoLanProbe(enabled: Boolean) {
        context.dataStore.edit { it[autoLanProbeKey] = enabled }
    }

    suspend fun setSyncCursor(cursor: Int) {
        context.dataStore.edit { it[syncCursorKey] = cursor }
    }

    suspend fun syncCursor(): Int = syncCursorFlow.first()

    suspend fun setLastSyncAt(iso: String) {
        context.dataStore.edit { it[lastSyncAtKey] = iso }
    }

    suspend fun setAutoSync(enabled: Boolean) {
        context.dataStore.edit { it[autoSyncKey] = enabled }
    }

    suspend fun setFhdHost(host: String) {
        context.dataStore.edit { it[fhdHost] = host.trim() }
    }

    suspend fun fhdHost(): String = fhdHostFlow.first()

    suspend fun saveFhdAuth(
        access: String,
        refresh: String,
        sessionId: String,
        username: String,
        userId: Int = 0,
    ) {
        context.dataStore.edit {
            it[fhdAccess] = access
            it[fhdRefresh] = refresh
            it[fhdSession] = sessionId
            it[fhdUsername] = username
            if (userId > 0) it[userIdKey] = userId
        }
    }

    val fcmTokenFlow: Flow<String> = context.dataStore.data.map { it[fcmTokenKey] ?: "" }

    suspend fun setFcmToken(token: String) {
        context.dataStore.edit { it[fcmTokenKey] = token }
    }

    suspend fun fcmToken(): String = fcmTokenFlow.first()

    suspend fun setMarketToken(token: String) {
        context.dataStore.edit { it[marketToken] = token.trim() }
    }

    suspend fun setMarketTokens(access: String, refresh: String = "") {
        context.dataStore.edit {
            it[marketToken] = access.trim()
            if (refresh.isNotBlank()) it[marketRefresh] = refresh.trim()
        }
    }

    suspend fun marketAccessToken(): String = marketTokenFlow.first()

    suspend fun marketRefreshToken(): String = marketRefreshFlow.first()

    suspend fun setServerMode(mode: String) {
        context.dataStore.edit { it[serverMode] = mode }
    }

    suspend fun setUserId(id: Int) {
        context.dataStore.edit { it[userIdKey] = id }
    }

    suspend fun setDisplayName(name: String) {
        context.dataStore.edit { it[fhdUsername] = name.trim() }
    }

    suspend fun legalAcceptedVersion(): String = legalAcceptedVersionFlow.first()

    suspend fun setLegalAcceptedVersion(version: String) {
        context.dataStore.edit { it[legalAcceptedVersionKey] = version.trim() }
    }

    suspend fun setThemeMode(mode: String) {
        context.dataStore.edit { it[themeModeKey] = mode }
    }

    suspend fun setBiometricEnabled(enabled: Boolean) {
        context.dataStore.edit { it[biometricEnabledKey] = enabled }
    }

    suspend fun clear() {
        context.dataStore.edit { it.clear() }
    }

    suspend fun accessToken(): String = fhdAccessFlow.first()
}
