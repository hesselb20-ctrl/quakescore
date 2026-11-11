package org.quakescore.collector

import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.util.Locale
import java.util.concurrent.TimeUnit
import java.util.zip.GZIPOutputStream

/** Server API v1. All calls are blocking; call them off the main thread. */
class Api(base: String) {
    private val root: HttpUrl = base.trimEnd('/').toHttpUrl()

    /**
     * Building footprints near a location rounded to 0.01 degrees (see README, "Building pick").
     * Returns the GeoJSON FeatureCollection text.
     */
    @Throws(IOException::class)
    fun footprints(latRounded: Double, lonRounded: Double): String {
        val url = root.newBuilder().addPathSegments("v1/footprints")
            .addQueryParameter("lat", String.format(Locale.ROOT, "%.2f", latRounded))
            .addQueryParameter("lon", String.format(Locale.ROOT, "%.2f", lonRounded))
            .build()
        return getText(url)
    }

    /** Whatever the server publishes for a building, shown as text on the main screen. */
    @Throws(IOException::class)
    fun buildingPublic(buildingId: String): String {
        val url = root.newBuilder().addPathSegments("v1/buildings").addPathSegment(buildingId)
            .addPathSegment("public").build()
        return getText(url)
    }

    /** POST /v1/sessions with a gzip-compressed JSON body. Returns the HTTP status code. */
    @Throws(IOException::class)
    fun uploadSession(json: ByteArray): Int {
        val body = gzip(json).toRequestBody("application/json".toMediaType())
        val req = Request.Builder().url(root.newBuilder().addPathSegments("v1/sessions").build())
            .header("Content-Encoding", "gzip")
            .post(body)
            .build()
        CLIENT.newCall(req).execute().use { return it.code }
    }

    /** DELETE /v1/sessions/{session_id}. The random session id is the capability. Returns the status code. */
    @Throws(IOException::class)
    fun deleteSession(sessionId: String): Int {
        val req = Request.Builder()
            .url(root.newBuilder().addPathSegments("v1/sessions").addPathSegment(sessionId).build())
            .delete()
            .build()
        CLIENT.newCall(req).execute().use { return it.code }
    }

    private fun getText(url: HttpUrl): String {
        val req = Request.Builder().url(url).get().build()
        CLIENT.newCall(req).execute().use { resp ->
            if (!resp.isSuccessful) throw IOException("HTTP ${resp.code}")
            return resp.body?.string() ?: ""
        }
    }

    companion object {
        private val CLIENT: OkHttpClient = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()

        fun gzip(data: ByteArray): ByteArray {
            val bos = ByteArrayOutputStream(data.size / 2 + 64)
            GZIPOutputStream(bos).use { it.write(data) }
            return bos.toByteArray()
        }
    }
}
