package org.quakescore.collector

import android.content.Context
import java.io.File

/**
 * App-private storage of finished sessions. Only the final feature JSON (upload schema v1) is ever
 * written; raw samples exist only in RAM inside SessionProcessor.
 */
object SessionStore {
    fun pendingDir(ctx: Context): File = File(ctx.filesDir, "sessions").apply { mkdirs() }
    private fun rejectedDir(ctx: Context): File = File(ctx.filesDir, "sessions_rejected").apply { mkdirs() }

    fun write(ctx: Context, sessionId: String, json: String): File {
        val dir = pendingDir(ctx)
        val tmp = File(dir, "$sessionId.tmp")
        tmp.writeText(json, Charsets.UTF_8)
        val dst = File(dir, "$sessionId.json")
        if (!tmp.renameTo(dst)) {
            tmp.delete()
            throw java.io.IOException("could not store session $sessionId")
        }
        return dst
    }

    fun pending(ctx: Context): List<File> =
        pendingDir(ctx).listFiles()?.filter { it.isFile && it.name.endsWith(".json") }?.sortedBy { it.name } ?: emptyList()

    /** Keeps a payload the server refused (4xx) out of the retry loop; removed by "delete my contributions". */
    fun reject(ctx: Context, f: File) {
        if (!f.renameTo(File(rejectedDir(ctx), f.name))) f.delete()
    }

    fun deleteAll(ctx: Context) {
        File(ctx.filesDir, "sessions").deleteRecursively()
        File(ctx.filesDir, "sessions_rejected").deleteRecursively()
    }
}
