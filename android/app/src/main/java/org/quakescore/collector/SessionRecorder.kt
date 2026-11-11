package org.quakescore.collector

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.os.BatteryManager
import android.os.Build
import android.os.SystemClock
import org.quakescore.dsp.SessionProcessor
import org.quakescore.dsp.SessionResult
import org.quakescore.dsp.TimeBase
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID
import kotlin.math.abs

/**
 * One recording session: accelerometer events (sensor time base) -> TimeBase (UTC) -> SessionProcessor.
 * Also collects the barometer median and battery state. Not thread-safe: use from the sensor thread,
 * except TimeBase.addPoint, which is synchronized.
 */
class SessionRecorder(private val ctx: Context, private val accel: Sensor, private val prefs: Prefs) {
    val sessionId: String = UUID.randomUUID().toString()
    val processor = SessionProcessor()
    val timeBase = TimeBase()
    val startedElapsedMs: Long = SystemClock.elapsedRealtime()
    val batteryStart: Int = Battery.percent(ctx)
    var chargingThroughout: Boolean = Battery.plugged(ctx)
        private set
    /** Set when the session cannot be used (for example an unexpected sensor time base). */
    var abortReason: String? = null
        private set

    private val pressure = ArrayList<Float>()
    private val ambient = ArrayList<Float>()
    private var checkedTimestampBase = false

    fun onAccel(ev: SensorEvent) {
        if (abortReason != null) return
        if (!checkedTimestampBase) {
            // Sensor timestamps are expected on the elapsedRealtimeNanos base. Batching delays delivery by
            // up to maxReportLatency, so allow a generous margin before declaring a different base.
            if (abs(SystemClock.elapsedRealtimeNanos() - ev.timestamp) > 120_000_000_000L) {
                abortReason = "sensor_timestamp_base"
                return
            }
            checkedTimestampBase = true
        }
        val utc = timeBase.map(ev.timestamp / 1e9)
        processor.push(utc, ev.values[0].toDouble(), ev.values[1].toDouble(), ev.values[2].toDouble())
    }

    fun onPressure(hPa: Float) {
        pressure.add(hPa)
    }

    fun onAmbientTemperature(c: Float) {
        ambient.add(c)
    }

    fun onPowerChanged(plugged: Boolean) {
        if (!plugged) chargingThroughout = false
    }

    val elapsedMs: Long get() = SystemClock.elapsedRealtime() - startedElapsedMs

    /**
     * Builds the upload JSON for a finished session, or returns null if there is nothing worth
     * uploading. Also writes a one-line summary for the main screen.
     */
    fun buildUpload(result: SessionResult, endReason: String): String? {
        val totalK = result.bands.values.sumOf { it.k }
        val usable = abortReason == null && totalK > 0 &&
            result.status != SessionProcessor.Status.TOO_SHORT && result.status != SessionProcessor.Status.NOT_FLAT
        prefs.lastSessionSummary = summary(result, endReason, usable)
        if (!usable) return null
        val buildingId = prefs.buildingId ?: return null
        val tempAmbient = Floor.median(ambient)
        val (floor, method, _) = Floor.forSession(prefs, Floor.median(pressure), tempAmbient, System.currentTimeMillis())
        val json = SessionJson.build(
            sessionId = sessionId,
            buildingId = buildingId,
            contributor = prefs.contributor(buildingId),
            phoneModel = "${Build.MANUFACTURER} ${Build.MODEL}",
            sensorName = accel.name,
            floor = floor,
            floorMethod = method,
            result = result,
            lsb = accel.resolution.toDouble(),
            sync = timeBase.report(),
            tempC = Battery.temperatureC(ctx),
            batteryStart = batteryStart,
            batteryEnd = Battery.percent(ctx),
            charging = chargingThroughout && Battery.plugged(ctx),
            appVersion = BuildConfig.VERSION_NAME,
        )
        return json.toString()
    }

    private fun summary(r: SessionResult, endReason: String, usable: Boolean): String {
        val start = if (r.tFirst.isFinite()) {
            SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.ROOT).format(Date((r.tFirst * 1000).toLong()))
        } else "-"
        val hours = if (r.duration.isFinite()) "%.1f h".format(Locale.ROOT, r.duration / 3600.0) else "-"
        val k = r.bands.entries.joinToString(" ") { "${it.key.name}=${it.value.k}" }
        val acc = "%.0f%%".format(Locale.ROOT, 100 * r.acceptFraction)
        val tail = if (usable) "queued for upload" else "nothing usable" + (abortReason?.let { " ($it)" } ?: "")
        return "$start, $hours, ended by $endReason; accepted $acc, windows $k; $tail"
    }
}

object Battery {
    private fun sticky(ctx: Context): Intent? = ctx.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED))

    fun percent(ctx: Context): Int {
        val bm = ctx.getSystemService(Context.BATTERY_SERVICE) as BatteryManager
        val p = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY)
        if (p in 0..100) return p
        val i = sticky(ctx) ?: return -1
        val level = i.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
        val scale = i.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
        return if (level >= 0 && scale > 0) level * 100 / scale else -1
    }

    /** On external power (charging or full). */
    fun plugged(ctx: Context): Boolean = (sticky(ctx)?.getIntExtra(BatteryManager.EXTRA_PLUGGED, 0) ?: 0) != 0

    fun temperatureC(ctx: Context): Double? {
        val t = sticky(ctx)?.getIntExtra(BatteryManager.EXTRA_TEMPERATURE, Int.MIN_VALUE) ?: return null
        return if (t == Int.MIN_VALUE) null else t / 10.0
    }
}
