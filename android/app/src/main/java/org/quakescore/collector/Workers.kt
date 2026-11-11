package org.quakescore.collector

import android.content.Context
import android.content.Intent
import androidx.work.BackoffPolicy
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * Uploads every stored session (POST /v1/sessions, gzip JSON). A file is deleted only after a 2xx
 * reply. 408, 429, 5xx and network errors retry with exponential backoff; other 4xx replies move the
 * file out of the queue. The server must treat session_id as an idempotency key, because a reply can
 * be lost after the server has stored the session.
 */
class UploadWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val ctx = applicationContext
        val prefs = Prefs(ctx)
        if (!prefs.consent) return@withContext Result.success()
        val api = Api(prefs.apiBase)
        var retry = false
        for (f in SessionStore.pending(ctx)) {
            val id = f.name.removeSuffix(".json")
            val code = try {
                api.uploadSession(f.readBytes())
            } catch (e: IOException) {
                retry = true
                continue
            }
            when {
                code in 200..299 -> {
                    f.delete()
                    prefs.uploadedIds = prefs.uploadedIds + id
                    prefs.sessionsContributed = prefs.sessionsContributed + 1
                }
                code == 408 || code == 429 || code >= 500 -> {
                    retry = true
                }
                else -> SessionStore.reject(ctx, f)
            }
        }
        if (retry) Result.retry() else Result.success()
    }

    companion object {
        fun enqueue(ctx: Context) {
            val prefs = Prefs(ctx)
            val constraints = Constraints.Builder()
                .setRequiredNetworkType(if (prefs.uploadOnMetered) NetworkType.CONNECTED else NetworkType.UNMETERED)
                .setRequiresCharging(prefs.uploadRequiresCharging)
                .build()
            val req = OneTimeWorkRequestBuilder<UploadWorker>()
                .setConstraints(constraints)
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 15, TimeUnit.MINUTES)
                .build()
            WorkManager.getInstance(ctx).enqueueUniqueWork("upload", ExistingWorkPolicy.APPEND_OR_REPLACE, req)
        }
    }
}

/**
 * Sends DELETE /v1/sessions/{id} for every session this install uploaded. The ids and server address
 * are kept in a separate preferences file that survives the wipe of the main settings, and are removed
 * once the server answers 2xx or 404.
 */
class DeletionWorker(ctx: Context, params: WorkerParameters) : CoroutineWorker(ctx, params) {
    override suspend fun doWork(): Result = withContext(Dispatchers.IO) {
        val sp = applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val base = sp.getString("base", null) ?: return@withContext Result.success()
        val ids = sp.getStringSet("ids", emptySet())!!.toMutableSet()
        val api = Api(base)
        var retry = false
        for (id in ids.toList()) {
            val code = try {
                api.deleteSession(id)
            } catch (e: IOException) {
                retry = true
                continue
            }
            if (code in 200..299 || code == 404) {
                ids.remove(id)
            } else {
                retry = true
            }
        }
        if (ids.isEmpty()) sp.edit().clear().apply() else sp.edit().putStringSet("ids", ids).apply()
        if (retry) Result.retry() else Result.success()
    }

    companion object {
        private const val PREFS = "qs_deletions"

        fun schedule(ctx: Context, base: String, ids: Set<String>) {
            if (ids.isEmpty()) return
            val sp = ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            val all = (sp.getStringSet("ids", emptySet())!! + ids).toSet()
            sp.edit().putString("base", base).putStringSet("ids", all).apply()
            val req = OneTimeWorkRequestBuilder<DeletionWorker>()
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 15, TimeUnit.MINUTES)
                .build()
            WorkManager.getInstance(ctx).enqueueUniqueWork("delete", ExistingWorkPolicy.REPLACE, req)
        }
    }
}

/** "Delete my contributions and stop". */
object Contributions {
    fun deleteAndStop(ctx: Context) {
        val app = ctx.applicationContext
        val prefs = Prefs(app)
        val ids = prefs.uploadedIds
        val base = prefs.apiBase
        prefs.consent = false
        app.stopService(Intent(app, RecordingService::class.java))
        WorkManager.getInstance(app).cancelUniqueWork("upload")
        SessionStore.deleteAll(app)
        DeletionWorker.schedule(app, base, ids)
        // New install secret on the next opt-in, so old and new contributor codes cannot be linked.
        prefs.wipe()
    }
}
