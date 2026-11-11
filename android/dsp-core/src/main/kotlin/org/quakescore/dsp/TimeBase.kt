package org.quakescore.dsp

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.sqrt

/**
 * Maps the sensor clock (elapsed-realtime seconds) to UTC seconds (DESIGN.md 3.1 item 2).
 *
 * Sync points are pairs (elapsed time, UTC - elapsed offset) with an uncertainty, taken at session
 * start, every 10 minutes and at session end. Offset and drift are fitted linearly (weighted least
 * squares). Samples must be mapped while the session runs, before later points exist, so the mapping
 * actually used is continuous and piecewise linear: it starts on the first point and, after each new
 * point, slews from the last mapped instant towards the current fit so that it meets the fit one
 * horizon (default 600 s, the sync interval) later. The slew is limited to +-200 ppm around the fitted
 * rate, so mapped time never jumps or runs backwards.
 *
 * The reported uncertainty combines the measurement uncertainty, the fit residual and the largest
 * difference between the mapping used and the final fit: it describes the UTC stamps the grid was
 * actually built from.
 */
class TimeBase(
    private val horizonSec: Double = 600.0,
    private val maxSlew: Double = 2e-4,
) {
    class SyncPoint(val elapsedSec: Double, val offsetSec: Double, val sigmaSec: Double, val source: String)

    class Fit(val eRef: Double, val oRef: Double, val drift: Double) {
        fun offset(e: Double): Double = oRef + drift * (e - eRef)
        fun utc(e: Double): Double = e + offset(e)
    }

    class Report(
        /** "gnss", "ntp" or "none" (the worst source that entered the fit). */
        val source: String,
        /** Estimated error of the UTC stamps used, ms; -1 when source is "none". */
        val sigmaMs: Double,
        val nPoints: Int,
        val driftPpm: Double,
        val residualMs: Double,
        val maxMapDeviationMs: Double,
    )

    private val points = ArrayList<SyncPoint>()
    private var dirty = false
    private var e0 = Double.NaN
    private var u0 = Double.NaN
    private var slope = 1.0
    private var lastE = Double.NaN
    private var lastU = Double.NaN
    private val breaks = ArrayList<DoubleArray>()

    @Synchronized
    fun addPoint(p: SyncPoint) {
        // the same GNSS fix read twice is one point
        if (points.any { it.source == p.source && abs(it.elapsedSec - p.elapsedSec) < 1e-6 }) return
        points.add(p)
        dirty = true
    }

    @get:Synchronized
    val hasPoints: Boolean get() = points.isNotEmpty()

    private fun usable(): List<SyncPoint> {
        val real = points.filter { it.source != "none" }
        return if (real.isNotEmpty()) real else points.toList()
    }

    @Synchronized
    fun fit(): Fit? {
        val pts = usable()
        if (pts.isEmpty()) return null
        val w = DoubleArray(pts.size) {
            val s = pts[it].sigmaSec
            if (s.isFinite() && s > 0) 1.0 / (max(s, 1e-4) * max(s, 1e-4)) else 1.0
        }
        val sw = w.sum()
        var eRef = 0.0
        var oRef = 0.0
        for (i in pts.indices) {
            eRef += w[i] * pts[i].elapsedSec
            oRef += w[i] * pts[i].offsetSec
        }
        eRef /= sw
        oRef /= sw
        var sxx = 0.0
        var sxy = 0.0
        for (i in pts.indices) {
            val de = pts[i].elapsedSec - eRef
            sxx += w[i] * de * de
            sxy += w[i] * de * (pts[i].offsetSec - oRef)
        }
        val drift = if (pts.size >= 2 && sxx > 0) sxy / sxx else 0.0
        return Fit(eRef, oRef, drift)
    }

    /** UTC seconds for sensor elapsed seconds e. Calls must be in increasing e. */
    @Synchronized
    fun map(e: Double): Double {
        if (dirty || e0.isNaN()) rebuild(e)
        val u = u0 + (e - e0) * slope
        lastE = e
        lastU = u
        return u
    }

    private fun rebuild(e: Double) {
        dirty = false
        val f = fit() ?: throw IllegalStateException("TimeBase has no sync point")
        val rate = 1.0 + f.drift
        if (lastE.isNaN()) {
            e0 = e
            u0 = f.utc(e)
            slope = rate
        } else {
            e0 = lastE
            u0 = lastU
            val s = (f.utc(e0 + horizonSec) - u0) / horizonSec
            slope = s.coerceIn(rate - maxSlew, rate + maxSlew)
        }
        breaks.add(doubleArrayOf(e0, u0))
    }

    @Synchronized
    fun report(): Report {
        val pts = usable()
        val f = fit()
        if (pts.isEmpty() || f == null || pts.all { it.source == "none" }) {
            return Report("none", -1.0, pts.size, 0.0, 0.0, 0.0)
        }
        val source = if (pts.all { it.source == "gnss" }) "gnss" else "ntp"
        val sMeas = sqrt(pts.sumOf { val s = if (it.sigmaSec.isFinite()) it.sigmaSec else 0.0; s * s } / pts.size)
        val sRes = if (pts.size >= 3) {
            sqrt(pts.sumOf { val r = it.offsetSec - f.offset(it.elapsedSec); r * r } / (pts.size - 2))
        } else 0.0
        var dev = 0.0
        for (b in breaks) dev = max(dev, abs(b[1] - f.utc(b[0])))
        if (!lastE.isNaN()) dev = max(dev, abs(lastU - f.utc(lastE)))
        val m = max(sMeas, sRes)
        return Report(source, 1000.0 * sqrt(m * m + dev * dev), pts.size, 1e6 * f.drift, 1000.0 * sRes, 1000.0 * dev)
    }
}
