package org.quakescore.dsp

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.sqrt

/**
 * End-to-end check of SessionProcessor against process_session_streaming in
 * experiments/export_device_vectors.py.
 *
 * Exact: status, sample counts, grid rate, anchor indices, gate seconds, flagged seconds, session end,
 * window counts and the indices of accepted windows.
 *
 * Tolerance on the accumulators (mean CSD and mean |X|^4): RTOL = 2e-5 relative, which is float32
 * level (the reference stores window spectra as complex64 and accumulates in complex64; the exporter's
 * own sample-by-sample check showed errors below 1e-6). Diagonal terms and p4 are compared relative to
 * themselves; off-diagonal terms relative to sqrt(Gii * Gjj). Only bins above the noise floor are
 * compared, defined per axis as Gii > 1e-4 x the median of Gii over the band.
 */
class StreamingVectorTest {

    @Test
    fun streamA_200HzGrid_withTransient() = check("stream_a")

    @Test
    fun streamB_100HzGrid_endsOnFlaggedRun() = check("stream_b")

    @Test
    fun streamC_browserRate_upsampledTo100HzGrid() = check("stream_c")

    private fun check(name: String) {
        val exp = Vectors.json("${name}_expected.json")
        val meta = exp.obj("meta")
        val p = SessionProcessor()
        Vectors.feed("$name.csv.gz", meta.d("t0"), meta.d("lsb"), p)
        val r = p.finish()

        assertEquals(exp.s("status"), r.status.name.lowercase())
        assertEquals(exp.l("n_samples"), r.nRaw)
        assertEquals(exp.d("fs_g"), r.fsGrid, 0.0)
        assertEquals(exp.d("fs_probe"), r.fsProbe, 1e-9)
        assertEquals(exp.d("fs_raw"), r.fsRaw, 1e-9)
        assertEquals(exp.d("duration"), r.duration, 1e-9)
        assertEquals(exp.d("t_start"), r.tStart, 0.0)
        assertEquals(exp.l("j50"), r.j50)
        assertEquals(exp.l("n50"), r.n50)
        assertEquals(exp.l("nsec").toInt(), r.nSeconds)
        assertEquals(exp.getValue("flagged").longs().map { it.toInt() }, r.flaggedSeconds)
        if (exp.isNull("end_second")) assertNull(r.endSecond) else assertEquals(exp.l("end_second").toInt(), r.endSecond)
        assertEquals(exp.d("rms_med"), r.rmsMedian, 1e-9 * exp.d("rms_med"))
        val gExp = exp.getValue("g_vec").doubles()
        for (a in 0 until 3) assertEquals(gExp[a], r.gLevel!![a], 1e-10)
        assertEquals(exp.d("accept_fraction"), r.acceptFraction, 1e-12)

        val bands = exp.obj("bands")
        for (band in Band.entries) {
            val e = bands.obj(band.name)
            val got = r.bands.getValue(band)
            assertEquals("$name $band k", e.l("k").toInt(), got.k)
            assertEquals("$name $band n_total", e.l("n_total").toInt(), got.nTotal)
            assertEquals("$name $band windows", e.getValue("windows").longs(), got.windows)
            compare("$name $band", Packing.fromBase64(e.s("csd")), got.csd, Packing.fromBase64(e.s("p4")), got.p4)
        }
    }

    private fun compare(label: String, ec: FloatArray, ac: FloatArray, ep: FloatArray, ap: FloatArray) {
        assertEquals(NBINS * 9, ec.size)
        assertEquals(NBINS * 3, ep.size)
        val floor = DoubleArray(3) { i -> 1e-4 * Stats.median(DoubleArray(NBINS) { f -> ec[9 * f + i].toDouble() }) }
        if (floor.all { it == 0.0 }) {
            assertTrue("$label expected all zeros", ac.all { it == 0f } && ap.all { it == 0f })
            return
        }
        var worst = 0.0
        var checked = 0
        val pairs = arrayOf(intArrayOf(3, 0, 1), intArrayOf(5, 0, 2), intArrayOf(7, 1, 2))
        for (f in 0 until NBINS) {
            val g = DoubleArray(3) { ec[9 * f + it].toDouble() }
            for (i in 0 until 3) {
                if (g[i] <= floor[i]) continue
                worst = max(worst, rel(ac[9 * f + i], ec[9 * f + i], g[i], label, "G$i$i bin $f"))
                val p4 = ep[3 * f + i].toDouble()
                worst = max(worst, rel(ap[3 * f + i], ep[3 * f + i], p4, label, "p4[$i] bin $f"))
                checked++
            }
            for (pr in pairs) {
                if (g[pr[1]] <= floor[pr[1]] || g[pr[2]] <= floor[pr[2]]) continue
                val den = sqrt(g[pr[1]] * g[pr[2]])
                worst = max(worst, rel(ac[9 * f + pr[0]], ec[9 * f + pr[0]], den, label, "Re pair ${pr[0]} bin $f"))
                worst = max(worst, rel(ac[9 * f + pr[0] + 1], ec[9 * f + pr[0] + 1], den, label, "Im pair ${pr[0]} bin $f"))
            }
        }
        println("$label: compared $checked diagonal bins, worst relative error $worst")
        assertTrue("$label: too few bins above the floor ($checked)", checked > NBINS)
    }

    private fun rel(a: Float, e: Float, scale: Double, label: String, what: String): Double {
        val err = abs(a.toDouble() - e.toDouble()) / scale
        assertTrue("$label $what: got $a expected $e (relative ${err})", err <= RTOL)
        return err
    }

    companion object {
        const val RTOL = 2e-5
    }
}
