package org.quakescore.dsp

import kotlin.math.PI
import kotlin.math.ceil
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.sqrt

/**
 * Tier B extension point (not in v1). Would receive the scaled spectra of every accepted window so
 * that frequency-limited sync frames can be kept for bands L and M. Nothing in v1 sets it.
 */
fun interface WindowSpectraSink {
    /** spectra: [axis][bin][re, im] flattened, length 3 * NBINS * 2, float32-rounded as accumulated. */
    fun onAcceptedWindow(band: Band, windowIndex: Long, spectra: FloatArray)
}

/**
 * Window accumulator for one zoom band (pipeline.py _window_spectra and the accumulation loop).
 *
 * Window k covers band samples [1024 k, 1024 k + 2047] (absolute, epoch anchored). When its last
 * sample arrives the scaled spectra are computed (mean removal, linear detrend, periodic Hann, real
 * FFT, scale sqrt(2 / (fs * sum(w^2)))), rounded to float32 as the reference stores complex64, and the
 * window waits until the gate seconds it overlaps are known. Accepted windows add X_a conj(X_b) and
 * |X_a|^4 to double-precision sums.
 */
class BandAccumulator(val band: Band) {
    private val fs = band.fs
    private val ring = Array(3) { DoubleArray(NFFT) }
    private var first = Long.MIN_VALUE
    private val re = DoubleArray(NFFT)
    private val im = DoubleArray(NFFT)
    private val pending = ArrayDeque<Pending>()

    /** Sums over accepted windows, packed per bin as the upload: Gxx Gyy Gzz ReGxy ImGxy ReGxz ImGxz ReGyz ImGyz. */
    val csdSum = DoubleArray(NBINS * 9)
    /** Sums of |X_i|^4 per bin, axes x y z. */
    val p4Sum = DoubleArray(NBINS * 3)
    var accepted = 0
        private set
    var total = 0
        private set
    /** Absolute indices of accepted windows (about 1400 per 8 h in band H). */
    val acceptedWindows = ArrayList<Long>()

    var tierBSink: WindowSpectraSink? = null

    private class Pending(val k: Long, val spectra: FloatArray)

    /** Adds one levelled band sample. Returns true if a window completed. */
    fun push(a: Long, x: Double, y: Double, z: Double): Boolean {
        if (first == Long.MIN_VALUE) first = a
        val p = Math.floorMod(a, NFFT.toLong()).toInt()
        ring[0][p] = x; ring[1][p] = y; ring[2][p] = z
        if (Math.floorMod(a + 1, HOP.toLong()) != 0L) return false
        val start = a + 1 - NFFT
        if (start < first) return false
        pending.addLast(Pending(start / HOP, spectra(start)))
        total++
        return true
    }

    private fun spectra(start: Long): FloatArray {
        val out = FloatArray(3 * NBINS * 2)
        val s0 = Math.floorMod(start, NFFT.toLong()).toInt()
        for (axis in 0 until 3) {
            val r = ring[axis]
            var sum = 0.0
            for (i in 0 until NFFT) {
                val v = r[(s0 + i) and (NFFT - 1)]
                re[i] = v
                sum += v
            }
            val mean = sum / NFFT
            var sn = 0.0
            for (i in 0 until NFFT) {
                re[i] -= mean
                sn += re[i] * CENTRE[i]
            }
            val slope = sn / CENTRE_SQ_SUM
            for (i in 0 until NFFT) {
                re[i] = (re[i] - slope * CENTRE[i]) * HANN[i]
                im[i] = 0.0
            }
            FFT.transform(re, im)
            val scale = sqrt(2.0 / (fs * HANN_SQ_SUM))
            val base = axis * NBINS * 2
            for (f in 0 until NBINS) {
                out[base + 2 * f] = (re[f] * scale).toFloat()
                out[base + 2 * f + 1] = (im[f] * scale).toFloat()
            }
        }
        return out
    }

    /**
     * Decides pending windows in order (pipeline.py lines 128-135). flagCum[s] is the number of flagged
     * seconds before second s, for s in 0..nsec. With final == false a window waits until the decision
     * cannot change any more; with final == true every pending window is decided against nsec.
     */
    internal fun decide(nsec: Int, flagCum: IntArray, flat: Boolean, final: Boolean, secT0: Double) {
        while (pending.isNotEmpty()) {
            val w = pending.first()
            val tLo = (w.k * HOP).toDouble() / fs
            val tHi = tLo + NFFT / fs
            if (tLo < secT0) {                       // can never be inside
                pending.removeFirst()
                continue
            }
            val inside = tHi <= secT0 + nsec
            val rawHi = ceil(tHi - secT0)
            if (!final && (!inside || rawHi > nsec)) return
            pending.removeFirst()
            if (!inside) continue
            val sLo = floor(tLo - secT0).toLong().coerceIn(0L, nsec.toLong()).toInt()
            val sHi = rawHi.toLong().coerceIn(0L, nsec.toLong()).toInt()
            if (flat && flagCum[sHi] - flagCum[sLo] == 0) accumulate(w)
        }
    }

    private fun accumulate(w: Pending) {
        val s = w.spectra
        val yOff = NBINS * 2
        val zOff = NBINS * 4
        for (f in 0 until NBINS) {
            val xr = s[2 * f].toDouble(); val xi = s[2 * f + 1].toDouble()
            val yr = s[yOff + 2 * f].toDouble(); val yi = s[yOff + 2 * f + 1].toDouble()
            val zr = s[zOff + 2 * f].toDouble(); val zi = s[zOff + 2 * f + 1].toDouble()
            val pxx = xr * xr + xi * xi
            val pyy = yr * yr + yi * yi
            val pzz = zr * zr + zi * zi
            val c = 9 * f
            csdSum[c] += pxx
            csdSum[c + 1] += pyy
            csdSum[c + 2] += pzz
            // G_ab = X_a conj(X_b): re = ar br + ai bi, im = ai br - ar bi
            csdSum[c + 3] += xr * yr + xi * yi
            csdSum[c + 4] += xi * yr - xr * yi
            csdSum[c + 5] += xr * zr + xi * zi
            csdSum[c + 6] += xi * zr - xr * zi
            csdSum[c + 7] += yr * zr + yi * zi
            csdSum[c + 8] += yi * zr - yr * zi
            val q = 3 * f
            p4Sum[q] += pxx * pxx
            p4Sum[q + 1] += pyy * pyy
            p4Sum[q + 2] += pzz * pzz
        }
        accepted++
        acceptedWindows.add(w.k)
        tierBSink?.onAcceptedWindow(band, w.k, s)
    }

    /** Mean one-sided CSD, packed per bin (9 floats), as uploaded. Zeros when no window was accepted. */
    fun csdMean(): FloatArray = FloatArray(NBINS * 9) { if (accepted == 0) 0f else (csdSum[it] / accepted).toFloat() }

    /** Mean |X_i|^4 per bin (3 floats), as uploaded. */
    fun p4Mean(): FloatArray = FloatArray(NBINS * 3) { if (accepted == 0) 0f else (p4Sum[it] / accepted).toFloat() }

    companion object {
        private val FFT = Fft(NFFT)

        /** scipy.signal.get_window("hann", NFFT, fftbins=True), built the way scipy builds it. */
        val HANN: DoubleArray = run {
            val step = (PI - (-PI)) / NFFT          // numpy.linspace(-pi, pi, NFFT + 1) step
            DoubleArray(NFFT) { 0.5 + 0.5 * cos(it * step + (-PI)) }
        }
        val HANN_SQ_SUM: Double = HANN.fold(0.0) { acc, v -> acc + v * v }

        /** n = arange(NFFT) - (NFFT - 1) / 2, the detrend abscissa. */
        private val CENTRE = DoubleArray(NFFT) { it - (NFFT - 1) / 2.0 }
        private val CENTRE_SQ_SUM: Double = CENTRE.fold(0.0) { acc, v -> acc + v * v }
    }
}
