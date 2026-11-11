package org.quakescore.dsp

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.double
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.long
import java.io.File
import java.util.zip.GZIPInputStream

/** Access to <repo>/tests/vectors, written by experiments/export_device_vectors.py. */
object Vectors {
    val dir: File = File(System.getProperty("qs.vectors") ?: "../../tests/vectors")

    fun json(name: String): JsonObject = Json.parseToJsonElement(File(dir, name).readText()).jsonObject

    fun <T> lines(name: String, block: (Sequence<String>) -> T): T =
        GZIPInputStream(File(dir, name).inputStream()).bufferedReader().useLines(block)

    /** Feeds a stream_*.csv.gz file into a processor exactly as the export script rebuilds it. */
    fun feed(name: String, t0: Double, lsb: Double, p: SessionProcessor) {
        var off = 0L
        lines(name) { seq ->
            seq.forEach { line ->
                if (line.isNotBlank()) {
                    val f = line.split(',')
                    off += f[0].toLong()
                    p.push(
                        t0 + off.toDouble() * 1e-9,
                        f[1].toLong().toDouble() * lsb,
                        f[2].toLong().toDouble() * lsb,
                        f[3].toLong().toDouble() * lsb,
                    )
                }
            }
        }
    }
}

fun JsonObject.d(key: String): Double = getValue(key).jsonPrimitive.double
fun JsonObject.l(key: String): Long = getValue(key).jsonPrimitive.long
fun JsonObject.s(key: String): String = getValue(key).jsonPrimitive.content
fun JsonObject.obj(key: String): JsonObject = getValue(key).jsonObject
fun JsonObject.arr(key: String): JsonArray = getValue(key).jsonArray
fun JsonObject.isNull(key: String): Boolean = getValue(key) is JsonNull
fun JsonElement.doubles(): DoubleArray = jsonArray.map { it.jsonPrimitive.double }.toDoubleArray()
fun JsonElement.longs(): List<Long> = jsonArray.map { it.jsonPrimitive.long }
