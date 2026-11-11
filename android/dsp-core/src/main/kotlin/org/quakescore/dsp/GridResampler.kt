package org.quakescore.dsp

import kotlin.math.ceil
import kotlin.math.floor

/**
 * Epoch-anchored linear interpolation onto the uniform grid t_i = i / fsG (pipeline.py step 1).
 *
 * Mirrors numpy.interp exactly for an increasing stream: grid point i is emitted once the first raw
 * sample with t > t_i has arrived; t_i == t_a returns the sample value, t_i before the first sample
 * returns the first value, and the grid ends at floor(t_last * fsG) holding the last value.
 * Samples whose time does not increase are rejected (returns false).
 */
class GridResampler(val fsG: Double, private val sink: Sink3) {
    private var hasPrev = false
    private var ta = 0.0
    private var xa = 0.0
    private var ya = 0.0
    private var za = 0.0
    private var next = 0L

    /** Absolute grid index of the first emitted grid point (valid after the first sample). */
    var firstIndex: Long = Long.MIN_VALUE
        private set

    fun push(t: Double, x: Double, y: Double, z: Double): Boolean {
        if (!hasPrev) {
            ta = t; xa = x; ya = y; za = z
            next = ceil(t * fsG).toLong()
            firstIndex = next
            hasPrev = true
            return true
        }
        if (!(t > ta)) return false
        val dt = t - ta
        val sx = (x - xa) / dt
        val sy = (y - ya) / dt
        val sz = (z - za) / dt
        while (true) {
            val tg = next.toDouble() / fsG
            if (!(tg < t)) break
            if (tg <= ta) {
                sink.accept(next, xa, ya, za)
            } else {
                val d = tg - ta
                sink.accept(next, sx * d + xa, sy * d + ya, sz * d + za)
            }
            next++
        }
        ta = t; xa = x; ya = y; za = z
        return true
    }

    /** Emits the remaining grid points up to floor(t_last * fsG) with the last value. */
    fun finish() {
        if (!hasPrev) return
        val last = floor(ta * fsG).toLong()
        while (next <= last) {
            sink.accept(next, xa, ya, za)
            next++
        }
    }
}
