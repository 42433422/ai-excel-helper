package com.xiuci.xcagi.mobile.core.network

import com.google.gson.Gson
import com.google.gson.JsonParser
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.BufferedReader
import java.io.InputStreamReader
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SseChatClient @Inject constructor(
    private val okHttp: OkHttpClient,
    private val serverRouter: ServerRouter,
) {
    private val gson = Gson()

    suspend fun streamChat(
        message: String,
        bearer: String,
        userId: Int,
        useCloud: Boolean = false,
        onToken: (String) -> Unit,
        onDone: (String) -> Unit,
        onError: (String) -> Unit,
    ) = withContext(Dispatchers.IO) {
        val url = if (useCloud) {
            "${serverRouter.modstoreBaseUrl()}api/agent/butler/chat/stream"
        } else {
            "${serverRouter.fhdBaseUrl()}api/ai/chat/stream"
        }
        val bodyJson = if (useCloud) {
            gson.toJson(
                mapOf(
                    "messages" to listOf(mapOf("role" to "user", "content" to message)),
                    "max_tokens" to 4096,
                ),
            )
        } else {
            gson.toJson(mapOf("message" to message))
        }
        val reqBuilder = Request.Builder()
            .url(url)
            .post(bodyJson.toRequestBody("application/json".toMediaType()))
            .header("Accept", "text/event-stream")
            .header("X-XCAGI-Client", "android")
        if (bearer.isNotBlank()) {
            reqBuilder.header("Authorization", bearer)
        }
        if (userId > 0) {
            reqBuilder.header("X-User-ID", userId.toString())
        }
        val req = reqBuilder.build()
        try {
            okHttp.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) {
                    val hint = if (useCloud) "云端对话 HTTP ${resp.code}" else "HTTP ${resp.code}"
                    onError(hint)
                    return@withContext
                }
                val reader = BufferedReader(InputStreamReader(resp.body!!.byteStream()))
                val buf = StringBuilder()
                var line: String?
                while (reader.readLine().also { line = it } != null) {
                    val l = line!!.trim()
                    if (!l.startsWith("data:")) continue
                    val payload = l.removePrefix("data:").trim()
                    if (payload.isBlank() || payload == "[DONE]") continue
                    try {
                        val json = JsonParser.parseString(payload).asJsonObject
                        if (useCloud) {
                            json.get("error")?.asString?.takeIf { it.isNotBlank() }?.let {
                                onError(it)
                                return@withContext
                            }
                            val t = json.get("text")?.asString ?: ""
                            if (t.isNotEmpty()) {
                                buf.append(t)
                                onToken(t)
                            }
                            if (json.get("done")?.asBoolean == true) {
                                onDone(buf.toString().ifBlank { "（无回复）" })
                                return@withContext
                            }
                        } else {
                            when (json.get("type")?.asString) {
                                "token" -> {
                                    val t = json.get("text")?.asString ?: ""
                                    if (t.isNotEmpty()) {
                                        buf.append(t)
                                        onToken(t)
                                    }
                                }
                                "done" -> {
                                    val result = json.get("result")
                                    val finalText = when {
                                        result == null -> buf.toString()
                                        result.isJsonObject -> result.asJsonObject.get("response")?.asString ?: buf.toString()
                                        else -> result.asString
                                    }
                                    onDone(finalText.ifBlank { buf.toString() })
                                    return@withContext
                                }
                                "error" -> onError(json.get("message")?.asString ?: "stream error")
                            }
                        }
                    } catch (_: Exception) {
                    }
                }
                onDone(buf.toString().ifBlank { "（无回复）" })
            }
        } catch (e: Exception) {
            onError(e.message ?: "连接失败")
        }
    }
}
