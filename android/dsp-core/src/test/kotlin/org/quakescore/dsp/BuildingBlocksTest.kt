package org.quakescore.dsp

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.sin
import kotlin.random.Random

class BuildingBlocksTest {

    @Test
    fun firTapsAreBitIdenticalToPython() {
        val j = Vectors.json("fir_taps.json")
        for ((m, taps) in listOf(4 to FirTaps.M4, 2 to FirTaps.M2)) {
            val exp = j.getValue(m.toString()).doubles()
            assertEquals(if (m == 4) 209 else 105, taps.size)
            assertEquals(exp.size, taps.size)
            for (i in exp.indices) assertEquals("m=$m tap $i", exp[i].toRawBits(), taps[i].toRawBits())
        }
    }

    @Test
    fun decimatorMatchesDecimateAnchored() {
        val j = Vectors.json("decimate_case.json")
        val x = j.arr("x").map { it.doubles() }
        for (c in j.arr("cases")) {
            val case = c as kotlinx.serialization.json.JsonObject
            val m = case.l("m").toInt()
            val i0 = case.l("i0")
            val y = case.arr("y").map { it.doubles() }
            val got = ArrayList<Pair<Long, DoubleArray>>()
            val d = AnchoredDecimator(m) { idx, a, b, z -> got.add(idx to doubleArrayOf(a, b, z)) }
            x.forEachIndexed { r, v -> d.push(i0 + r, v[0], v[1], v[2]) }
            assertEquals("m=$m count", y.size, got.size)
            assertEquals("m=$m j0", case.l("j0"), got[0].first)
            for (r in y.indices) {
                assertEquals(case.l("j0") + r, got[r].first)
                assertArrayEquals("m=$m row $r", y[r], got[r].second, 1e-11)
            }
        }
    }

    @Test
    fun fftMatchesDirectDft() {
        val n = NFFT
        val rnd = Random(5)
        val xr = DoubleArray(n) { rnd.nextDouble(-1.0, 1.0) }
        val xi = DoubleArray(n) { rnd.nextDouble(-1.0, 1.0) }
        val re = xr.copyOf()
        val im = xi.copyOf()
        Fft(n).transform(re, im)
        var worst = 0.0
        for (k in intArrayOf(0, 1, 2, 17, 511, 1024, 1500, n - 1)) {
            var sr = 0.0
            var si = 0.0
            for (t in 0 until n) {
                val a = -2.0 * PI * ((k.toLong() * t) % n) / n
                sr += xr[t] * cos(a) - xi[t] * sin(a)
                si += xr[t] * sin(a) + xi[t] * cos(a)
            }
            worst = max(worst, max(abs(sr - re[k]), abs(si - im[k])))
        }
        assertTrue("fft error $worst", worst < 1e-9)
    }

    @Test
    fun gridReproducesNumpyInterpRules() {
        val out = ArrayList<Pair<Long, Double>>()
        val g = GridResampler(200.0) { i, x, _, _ -> out.add(i to x) }
        // samples at 0.0012, 0.0050 (exactly grid 1), 0.0123, 0.0151
        g.push(0.0012, 1.0, 0.0, 0.0)
        g.push(0.0050, 2.0, 0.0, 0.0)
        g.push(0.0123, 3.0, 0.0, 0.0)
        g.push(0.0151, 4.0, 0.0, 0.0)
        g.finish()
        // grid 1 (0.005) equals a sample time, grid 2 (0.010) interpolated, grid 3 (0.015) interpolated
        assertEquals(listOf(1L, 2L, 3L), out.map { it.first })
        assertEquals(2.0, out[0].second, 0.0)
        assertEquals(2.0 + (0.010 - 0.0050) / (0.0123 - 0.0050), out[1].second, 1e-12)
        assertEquals(3.0 + (0.015 - 0.0123) / (0.0151 - 0.0123), out[2].second, 1e-12)
        assertTrue(!GridResampler(200.0) { _, _, _, _ -> }.let { it.push(1.0, 0.0, 0.0, 0.0); it.push(1.0, 0.0, 0.0, 0.0) })
    }

    @Test
    fun levellingPutsGravityOnZ() {
        val g = doubleArrayOf(0.3, -0.5, 9.78)
        val r = Levelling.rotation(g)
        val gz = r[2][0] * g[0] + r[2][1] * g[1] + r[2][2] * g[2]
        val gx = r[0][0] * g[0] + r[0][1] * g[1] + r[0][2] * g[2]
        val gy = r[1][0] * g[0] + r[1][1] * g[1] + r[1][2] * g[2]
        assertEquals(Vec3.norm(g), gz, 1e-12)
        assertEquals(0.0, gx, 1e-12)
        assertEquals(0.0, gy, 1e-12)
    }

    @Test
    fun packingRoundTrips() {
        val v = floatArrayOf(1.5f, -2.25e-12f, 0f, Float.MIN_VALUE, 3.4e38f)
        assertArrayEquals(v, Packing.fromBase64(Packing.toBase64(v)), 0f)
        // little endian: 1.0f is 00 00 80 3F
        assertEquals("AACAPw==", Packing.toBase64(floatArrayOf(1f)))
    }

    @Test
    fun timeBaseFitsDriftAndStaysContinuous() {
        val tb = TimeBase()
        val off0 = 1.79e9 + 0.0123
        val drift = 30e-6
        fun truth(e: Double) = off0 + drift * (e - 1000.0)
        tb.addPoint(TimeBase.SyncPoint(1000.0, truth(1000.0), 0.002, "ntp"))
        var prev = Double.NEGATIVE_INFINITY
        var e = 1000.0
        while (e < 1000.0 + 3 * 3600) {
            if (abs((e - 1000.0) % 600.0) < 1e-9 && e > 1000.0) tb.addPoint(TimeBase.SyncPoint(e, truth(e), 0.002, "ntp"))
            val u = tb.map(e)
            assertTrue("monotonic at $e", u > prev)
            prev = u
            e += 0.5
        }
        val f = tb.fit()!!
        assertEquals(drift, f.drift, 1e-9)
        val rep = tb.report()
        assertEquals("ntp", rep.source)
        assertTrue("sigma ${rep.sigmaMs}", rep.sigmaMs > 0 && rep.sigmaMs < 1000.0)
        assertEquals("none", TimeBase().report().source)
    }
}
