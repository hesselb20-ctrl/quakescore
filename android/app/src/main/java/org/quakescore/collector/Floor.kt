package org.quakescore.collector

import android.content.Context
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Handler
import android.os.Looper
import kotlin.math.ln
import kotlin.math.roundToInt

/** Barometric floor estimate (DESIGN.md 3.2, method "baro_entry"). */
object Floor {
    const val STOREY_M = 3.2
    /** A ground reading older than this is not compared with a session median (weather moves pressure). */
    const val GROUND_MAX_AGE_MS = 3L * 3600 * 1000

    /** Height above the reference: 8434 m * ln(p_ground / p), scaled by (273.15 + T) / 288.15 if T is known. */
    fun heightM(pGroundHpa: Double, pHpa: Double, tempC: Double?): Double {
        val dh = 8434.0 * ln(pGroundHpa / pHpa)
        return if (tempC != null) dh * (273.15 + tempC) / 288.15 else dh
    }

    fun floorOf(dh: Double): Int = (dh / STOREY_M).roundToInt()

    /**
     * Floor for a finished session. Manual entry wins. With a barometer: if the entrance reading is
     * recent, the session median is compared with it; otherwise the estimate made at setup (entrance
     * and resting spot measured minutes apart) is used. Returns (floor, method, height or NaN).
     */
    fun forSession(prefs: Prefs, pSessionHpa: Double?, tempC: Double?, nowMs: Long): Triple<Int, String, Double> {
        val stored = prefs.floor ?: 0
        val method = prefs.floorMethod ?: "manual"
        if (method == "manual") return Triple(stored, "manual", Double.NaN)
        val pg = prefs.pGroundHpa
        if (pSessionHpa != null && pg.isFinite() && nowMs - prefs.pGroundAtMs in 0..GROUND_MAX_AGE_MS) {
            val dh = heightM(pg, pSessionHpa, tempC)
            return Triple(floorOf(dh), "baro_entry", dh)
        }
        return Triple(stored, method, prefs.floorDh)
    }

    fun hasBarometer(ctx: Context): Boolean =
        (ctx.getSystemService(Context.SENSOR_SERVICE) as SensorManager).getDefaultSensor(Sensor.TYPE_PRESSURE) != null

    /**
     * Median of one sensor's first value over durationMs (pressure in hPa, ambient temperature in C).
     * Calls back on the main thread with null if the sensor is missing or reported nothing.
     */
    fun medianReading(ctx: Context, sensorType: Int, durationMs: Long, cb: (Double?) -> Unit) {
        val sm = ctx.getSystemService(Context.SENSOR_SERVICE) as SensorManager
        val sensor = sm.getDefaultSensor(sensorType)
        val main = Handler(Looper.getMainLooper())
        if (sensor == null) {
            main.post { cb(null) }
            return
        }
        val values = ArrayList<Float>()
        val listener = object : SensorEventListener {
            override fun onSensorChanged(event: SensorEvent) {
                values.add(event.values[0])
            }

            override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}
        }
        sm.registerListener(listener, sensor, SensorManager.SENSOR_DELAY_NORMAL, main)
        main.postDelayed({
            sm.unregisterListener(listener)
            cb(median(values))
        }, durationMs)
    }

    fun median(values: List<Float>): Double? {
        if (values.isEmpty()) return null
        val s = values.sorted()
        val n = s.size
        return if (n % 2 == 1) s[n / 2].toDouble() else (s[n / 2 - 1].toDouble() + s[n / 2].toDouble()) / 2.0
    }
}
