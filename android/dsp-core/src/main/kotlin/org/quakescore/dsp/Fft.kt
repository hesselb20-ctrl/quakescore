package org.quakescore.dsp

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

/**
 * Iterative radix-2 complex FFT, forward sign convention X[k] = sum_t x[t] exp(-2 pi i k t / n),
 * the same as numpy.fft. Not thread-safe only in the sense that callers own the arrays; the tables are
 * read-only, so one instance can be shared.
 */
class Fft(val n: Int) {
    init {
        require(n >= 2 && (n and (n - 1)) == 0) { "n must be a power of two" }
    }

    private val levels = Integer.numberOfTrailingZeros(n)
    private val cosT = DoubleArray(n / 2) { cos(2.0 * PI * it / n) }
    private val sinT = DoubleArray(n / 2) { sin(2.0 * PI * it / n) }
    private val rev = IntArray(n) { Integer.reverse(it) ushr (32 - levels) }

    /** In-place forward transform of (re, im), both of length n. */
    fun transform(re: DoubleArray, im: DoubleArray) {
        require(re.size == n && im.size == n)
        for (i in 0 until n) {
            val j = rev[i]
            if (j > i) {
                val tr = re[i]; re[i] = re[j]; re[j] = tr
                val ti = im[i]; im[i] = im[j]; im[j] = ti
            }
        }
        var size = 2
        while (size <= n) {
            val half = size / 2
            val step = n / size
            var start = 0
            while (start < n) {
                var t = 0
                for (j in start until start + half) {
                    val l = j + half
                    val c = cosT[t]
                    val s = sinT[t]
                    // (re[l] + i im[l]) * (c - i s)
                    val tr = re[l] * c + im[l] * s
                    val ti = im[l] * c - re[l] * s
                    re[l] = re[j] - tr
                    im[l] = im[j] - ti
                    re[j] += tr
                    im[j] += ti
                    t += step
                }
                start += size
            }
            size *= 2
        }
    }
}
