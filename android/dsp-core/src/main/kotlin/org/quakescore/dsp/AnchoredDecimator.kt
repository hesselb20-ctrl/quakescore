package org.quakescore.dsp

/**
 * Streaming form of pipeline.decimate_anchored: zero-phase FIR decimation by m where output sample j
 * sits at input absolute index j*m.
 *
 * y_j = sum_k h[k] * x[j*m + half - k], emitted when input index j*m + half arrives, for every j with
 * j*m - half >= i0 (the first input index). This is the same set of outputs and the same centre-tap
 * indexing as decimate_anchored (c0 = first multiple of m at or after i0 + half). Inputs must arrive
 * with consecutive absolute indices.
 */
class AnchoredDecimator(val m: Int, private val sink: Sink3) {
    private val h: DoubleArray = FirTaps.forFactor(m)
    private val n = h.size
    val half = (n - 1) / 2
    private val rx = DoubleArray(n)
    private val ry = DoubleArray(n)
    private val rz = DoubleArray(n)
    private var first = Long.MIN_VALUE
    private var expected = 0L

    init {
        require((n - 1) % (2 * m) == 0) { "numtaps - 1 must be a multiple of 2*m" }
    }

    fun push(a: Long, x: Double, y: Double, z: Double) {
        if (first == Long.MIN_VALUE) {
            first = a
            expected = a
        }
        require(a == expected) { "non-consecutive input index $a, expected $expected" }
        expected = a + 1
        val p = Math.floorMod(a, n.toLong()).toInt()
        rx[p] = x; ry[p] = y; rz[p] = z
        if (Math.floorMod(a - half, m.toLong()) == 0L && a - 2L * half >= first) {
            var sx = 0.0
            var sy = 0.0
            var sz = 0.0
            var q = p
            for (k in 0 until n) {
                val hk = h[k]
                sx += hk * rx[q]
                sy += hk * ry[q]
                sz += hk * rz[q]
                q = if (q == 0) n - 1 else q - 1
            }
            sink.accept((a - half) / m, sx, sy, sz)
        }
    }
}
