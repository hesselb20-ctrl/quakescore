package org.quakescore.collector

import android.hardware.SensorEvent
import kotlin.math.abs
import kotlin.math.acos
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/**
 * Pre-session check at a low sampling rate: the phone must be flat (within 15 degrees of horizontal,
 * face up or down) and still for [requiredSeconds] consecutive seconds before a session starts.
 *
 * STILL_RMS and STILL_TILT_STEP are provisional starting values, not measured ones. To be measured:
 * log the per-second RMS and tilt step on several phones lying on a bedside table (still) and while
 * being handled, and set the thresholds between the two distributions.
 */
class StillnessDetector(private val requiredSeconds: Int = 120) {
    private var second = Long.MIN_VALUE
    private var n = 0
    private val s = DoubleArray(3)
    private val ss = DoubleArray(3)
    private var prev: DoubleArray? = null
    var stillSeconds = 0
        private set

    /** Returns true once the phone has been flat and still for the required time. */
    fun add(ev: SensorEvent): Boolean {
        val sec = ev.timestamp / 1_000_000_000L
        if (sec != second) {
            if (second != Long.MIN_VALUE) {
                if (n >= 2) closeSecond() else stillSeconds = 0
                if (sec - second > 1) stillSeconds = 0          // gap in the stream
            }
            second = sec
            n = 0
            s.fill(0.0)
            ss.fill(0.0)
        }
        for (a in 0 until 3) {
            val v = ev.values[a].toDouble()
            s[a] += v
            ss[a] += v * v
        }
        n++
        return stillSeconds >= requiredSeconds
    }

    private fun closeSecond() {
        val m = DoubleArray(3) { s[it] / n }
        var varSum = 0.0
        for (a in 0 until 3) varSum += max(0.0, ss[a] / n - m[a] * m[a])
        val rms = sqrt(varSum / 3.0)
        val norm = sqrt(m[0] * m[0] + m[1] * m[1] + m[2] * m[2])
        val flat = norm > 0 && abs(m[2]) / norm >= FLAT_COS
        val p = prev
        val step = if (p == null) 0.0 else {
            val pn = sqrt(p[0] * p[0] + p[1] * p[1] + p[2] * p[2])
            val c = (p[0] * m[0] + p[1] * m[1] + p[2] * m[2]) / max(pn * norm, 1e-9)
            acos(min(1.0, max(-1.0, c)))
        }
        prev = m
        stillSeconds = if (flat && rms < STILL_RMS && step < STILL_TILT_STEP) stillSeconds + 1 else 0
    }

    companion object {
        const val FLAT_COS = 0.966            // cos(15 deg), as DeviceConfig.flat_cos
        const val STILL_RMS = 0.05            // m/s^2, provisional
        const val STILL_TILT_STEP = 0.01      // rad between consecutive one-second means, provisional
    }
}
