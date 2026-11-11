/*
 * Streaming on-device feature pipeline (DESIGN.md section 3.1), mirroring
 * quakescore/device/pipeline.py process_session step for step.
 *
 * Why this is not literally process_session
 * -----------------------------------------
 * The reference sees the whole session at once: it measures the raw rate over the whole recording,
 * takes gravity and the gate thresholds from session-wide medians, and levels with the mean of all
 * accepted seconds. A phone cannot hold a night of raw samples, so this class uses the following
 * streaming-equivalent rules. experiments/export_device_vectors.py (process_session_streaming) applies
 * the same rules with the reference building blocks and produces the test vectors in tests/vectors.
 *
 *  0. Grid rate. Raw samples are buffered until they span at least 10 s (rateProbeSeconds). The rate
 *     over that probe, (n - 1) / span, chooses the grid: 200 Hz if >= 190 Hz, else 100 Hz. The buffer
 *     is then replayed. fs_raw reported for the session is still (n - 1) / (t_last - t_first) over all
 *     accepted samples, as in the reference.
 *  1. Grid and privacy decimation are exactly the reference (GridResampler, AnchoredDecimator).
 *  a. Warm-up. The first 120 complete one-second blocks of the 50 Hz stream (the phone is required to
 *     be still already) give: the component-wise median of the block means (gravity direction used for
 *     the tilt test and the flat test), the median block RMS, and the levelling gravity = mean of the
 *     block means of the warm-up seconds that are not flagged against those statistics (else the
 *     median). The 50 Hz warm-up samples (6000 x 3 doubles) are buffered and replayed through the
 *     levelling rotation once it is known, so no data are lost.
 *  b. These values are frozen for the session. Every later second is flagged if its RMS exceeds
 *     5 x the warm-up median RMS, or its mean vector tilts more than 0.0035 rad from the warm-up gravity
 *     direction. If the warm-up gravity is not within 15 degrees of vertical the session ends with no
 *     accepted windows (status NOT_FLAT).
 *  c. A window is dropped if it overlaps any flagged second, using the reference's own
 *     floor/ceil-of-seconds test (t_lo, t_lo + NFFT/fs against j50/50). Per-second flags are kept as a
 *     cumulative count, and a window is decided only once every second it overlaps is known; for the
 *     long L and M windows that is when the window completes, for H a few samples later.
 *  d. If more than 60 consecutive seconds are flagged, the session ends at the end of that second:
 *     no further 50 Hz sample is used, which equals truncating the reference's 50 Hz stream there.
 *     Warm-up seconds count towards the run.
 *  Levelling uses the construction of pipeline.level_rotation.
 *
 * Arithmetic is double precision throughout; window spectra are rounded to float32 before they are
 * accumulated, because the reference stores them as complex64.
 */
package org.quakescore.dsp

import kotlin.math.acos
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

class SessionProcessor(val cfg: StreamConfig = StreamConfig()) {

    enum class Status(val terminal: Boolean) {
        PROBING(false), WARMUP(false), RUNNING(false),
        COMPLETE(true), ENDED_FLAGGED_RUN(true), NOT_FLAT(true), TOO_SHORT(true),
    }

    /** Optional observer of every completed one-second gate block (after the warm-up). */
    fun interface SecondListener {
        fun onSecond(index: Int, rms: Double, tilt: Double, flagged: Boolean)
    }

    var status: Status = Status.PROBING
        private set
    val ended: Boolean get() = status.terminal
    var secondListener: SecondListener? = null

    // raw stream
    var nRaw = 0L
        private set
    var nRejectedRaw = 0L
        private set
    private var tFirst = Double.NaN
    private var tLast = Double.NaN
    private var probe = DoubleArray(4 * 4096)
    private var probeN = 0
    var fsProbe = Double.NaN
        private set
    var fsGrid = Double.NaN
        private set
    private var grid: GridResampler? = null
    private var dec1: AnchoredDecimator? = null

    // 50 Hz stream and gate
    var j50 = Long.MIN_VALUE
        private set
    var n50 = 0L
        private set
    private val block = DoubleArray(150)
    private var blockN = 0
    private val warmN = cfg.warmupSeconds
    private val warm = DoubleArray(warmN * 50 * 3)
    private var warmRows = 0
    private val wMean = DoubleArray(warmN * 3)
    private val wRms = DoubleArray(warmN)
    private var nSecDone = 0
    private var flagCum = IntArray(4096)        // flagCum[s] = flagged seconds before s
    private var nFlags = 0                      // seconds whose flag is known
    private var run = 0
    private var gUnit = DoubleArray(3)
    var rmsMedian = Double.NaN
        private set
    var gMedian: DoubleArray? = null
        private set
    var gLevel: DoubleArray? = null
        private set
    private var rot: Array<DoubleArray>? = null
    private var flat = true

    // bands
    val bands: Map<Band, BandAccumulator> = Band.entries.associateWith { BandAccumulator(it) }
    private val bandH = bands.getValue(Band.H)
    private val bandM = bands.getValue(Band.M)
    private val bandL = bands.getValue(Band.L)
    private val decL = AnchoredDecimator(4) { j, x, y, z -> if (bandL.push(j, x, y, z)) decideAll(false) }
    private val decM = AnchoredDecimator(4) { j, x, y, z ->
        if (bandM.push(j, x, y, z)) decideAll(false)
        decL.push(j, x, y, z)
    }

    /** Adds one raw sample: t in UTC seconds, acceleration in m/s^2 in the device frame. */
    fun push(t: Double, x: Double, y: Double, z: Double) {
        if (nRaw > 0 && !(t > tLast)) {
            nRejectedRaw++
            return
        }
        if (nRaw == 0L) tFirst = t
        tLast = t
        nRaw++
        // Samples that arrive after the session has ended are counted (so the reported sample count,
        // raw rate and duration describe everything the recorder delivered) but not processed.
        if (status.terminal) return
        val g = grid
        if (g == null) {
            if (probeN * 4 + 4 > probe.size) probe = probe.copyOf(probe.size * 2)
            val b = probeN * 4
            probe[b] = t; probe[b + 1] = x; probe[b + 2] = y; probe[b + 3] = z
            probeN++
            if (t - tFirst >= cfg.rateProbeSeconds) startGrid()
        } else {
            g.push(t, x, y, z)
        }
    }

    private fun startGrid() {
        val span = probe[(probeN - 1) * 4] - probe[0]
        fsProbe = (probeN - 1) / span
        fsGrid = if (fsProbe >= 190.0) 200.0 else 100.0
        val d = AnchoredDecimator((fsGrid / 50.0).toInt()) { j, x, y, z -> on50(j, x, y, z) }
        dec1 = d
        val g = GridResampler(fsGrid) { i, x, y, z -> d.push(i, x, y, z) }
        grid = g
        status = Status.WARMUP
        for (i in 0 until probeN) {
            val b = i * 4
            g.push(probe[b], probe[b + 1], probe[b + 2], probe[b + 3])
            if (status.terminal) break
        }
        probe = DoubleArray(0)
        probeN = 0
    }

    private fun on50(j: Long, x: Double, y: Double, z: Double) {
        if (status.terminal) return
        if (j50 == Long.MIN_VALUE) j50 = j
        n50++
        if (rot != null) {
            levelPush(j, x, y, z)
        } else {
            val b = warmRows * 3
            warm[b] = x; warm[b + 1] = y; warm[b + 2] = z
            warmRows++
        }
        val b = blockN * 3
        block[b] = x; block[b + 1] = y; block[b + 2] = z
        blockN++
        if (blockN < 50) return
        blockN = 0
        var mx = 0.0; var my = 0.0; var mz = 0.0
        for (i in 0 until 50) {
            mx += block[3 * i]; my += block[3 * i + 1]; mz += block[3 * i + 2]
        }
        mx /= 50.0; my /= 50.0; mz /= 50.0
        var ss = 0.0
        for (i in 0 until 50) {
            val dx = block[3 * i] - mx
            val dy = block[3 * i + 1] - my
            val dz = block[3 * i + 2] - mz
            ss += dx * dx + dy * dy + dz * dz
        }
        val rms = sqrt(ss / 150.0)
        val s = nSecDone
        nSecDone++
        if (rot == null) {
            wMean[3 * s] = mx; wMean[3 * s + 1] = my; wMean[3 * s + 2] = mz
            wRms[s] = rms
            if (nSecDone == warmN) endWarmup()
            return
        }
        val tilt = tiltOf(mx, my, mz)
        val f = rms > cfg.gateRmsFactor * rmsMedian || tilt > cfg.gateTilt
        addFlag(f)
        secondListener?.onSecond(s, rms, tilt, f)
        if (run > cfg.maxFlaggedRun) end(Status.ENDED_FLAGGED_RUN) else decideAll(false)
    }

    private fun tiltOf(mx: Double, my: Double, mz: Double): Double {
        val nrm = sqrt(mx * mx + my * my + mz * mz)
        val c = (mx * gUnit[0] + my * gUnit[1] + mz * gUnit[2]) / max(nrm, 1e-9)
        return acos(min(max(c, -1.0), 1.0))
    }

    private fun addFlag(f: Boolean) {
        if (nFlags + 2 > flagCum.size) flagCum = flagCum.copyOf(flagCum.size * 2)
        flagCum[nFlags + 1] = flagCum[nFlags] + if (f) 1 else 0
        nFlags++
        run = if (f) run + 1 else 0
    }

    private fun endWarmup() {
        val col = DoubleArray(warmN)
        val gMed = DoubleArray(3) { a ->
            for (s in 0 until warmN) col[s] = wMean[3 * s + a]
            Stats.median(col)
        }
        gMedian = gMed
        val gn = Vec3.norm(gMed)
        gUnit = DoubleArray(3) { gMed[it] / gn }
        rmsMedian = Stats.median(wRms)
        val flags = BooleanArray(warmN) { s ->
            wRms[s] > cfg.gateRmsFactor * rmsMedian ||
                tiltOf(wMean[3 * s], wMean[3 * s + 1], wMean[3 * s + 2]) > cfg.gateTilt
        }
        val good = flags.count { !it }
        val gVec = if (good > 0) {
            val acc = DoubleArray(3)
            for (s in 0 until warmN) if (!flags[s]) for (a in 0 until 3) acc[a] += wMean[3 * s + a]
            DoubleArray(3) { acc[it] / good }
        } else gMed.copyOf()
        gLevel = gVec
        if (abs(gUnit[2]) < cfg.flatCos) {
            flat = false
            status = Status.NOT_FLAT
            return
        }
        rot = Levelling.rotation(gVec)
        var keep = warmN
        for (s in 0 until warmN) {
            addFlag(flags[s])
            if (run > cfg.maxFlaggedRun) {
                keep = s + 1
                break
            }
        }
        status = Status.RUNNING
        for (i in 0 until 50 * keep) {
            levelPush(j50 + i, warm[3 * i], warm[3 * i + 1], warm[3 * i + 2])
        }
        if (keep < warmN) end(Status.ENDED_FLAGGED_RUN) else decideAll(false)
    }

    private fun levelPush(j: Long, x: Double, y: Double, z: Double) {
        val r = rot!!
        val hx = r[0][0] * x + r[0][1] * y + r[0][2] * z
        val hy = r[1][0] * x + r[1][1] * y + r[1][2] * z
        val hz = r[2][0] * x + r[2][1] * y + r[2][2] * z
        if (bandH.push(j, hx, hy, hz)) decideAll(false)
        decM.push(j, hx, hy, hz)
    }

    private fun decideAll(final: Boolean) {
        if (rot == null) return
        val secT0 = j50 / 50.0
        for (b in BAND_ORDER) bands.getValue(b).decide(nFlags, flagCum, flat, final, secT0)
    }

    private fun end(s: Status) {
        status = s
        decideAll(true)
    }

    /** Ends the session (end of input, unplugging, time limit) and returns the features. */
    fun finish(): SessionResult {
        if (!status.terminal) {
            if (grid == null && probeN >= 2) startGrid()
            if (!status.terminal) grid?.finish()
            if (!status.terminal) {
                if (rot == null) status = Status.TOO_SHORT else end(Status.COMPLETE)
            }
        }
        return result()
    }

    fun result(): SessionResult {
        val flagged = ArrayList<Int>()
        for (s in 0 until nFlags) if (flagCum[s + 1] > flagCum[s]) flagged.add(s)
        var tot = 0
        var acc = 0
        val out = LinkedHashMap<Band, BandResult>()
        for (b in BAND_ORDER) {
            val a = bands.getValue(b)
            tot += a.total
            acc += a.accepted
            out[b] = BandResult(a.accepted, a.total, a.acceptedWindows.toList(), a.csdMean(), a.p4Mean())
        }
        val fsRaw = if (nRaw >= 2) (nRaw - 1) / (tLast - tFirst) else Double.NaN
        return SessionResult(
            status = status,
            tFirst = tFirst,
            tLast = tLast,
            tStart = 60.0 * Math.rint(tFirst / 60.0),
            duration = tLast - tFirst,
            fsRaw = fsRaw,
            fsProbe = fsProbe,
            fsGrid = fsGrid,
            nRaw = nRaw,
            j50 = j50,
            n50 = n50,
            nSeconds = nFlags,
            flaggedSeconds = flagged,
            endSecond = if (status == Status.ENDED_FLAGGED_RUN) nFlags - 1 else null,
            gMedian = gMedian?.copyOf(),
            gLevel = gLevel?.copyOf(),
            rmsMedian = rmsMedian,
            acceptFraction = acc.toDouble() / max(tot, 1),
            bands = out,
        )
    }

    companion object {
        private val BAND_ORDER = arrayOf(Band.L, Band.M, Band.H)
    }
}

class BandResult(
    val k: Int,
    val nTotal: Int,
    val windows: List<Long>,
    /** Mean CSD, NBINS x [Gxx, Gyy, Gzz, ReGxy, ImGxy, ReGxz, ImGxz, ReGyz, ImGyz]. */
    val csd: FloatArray,
    /** Mean |X_i|^4, NBINS x [x, y, z]. */
    val p4: FloatArray,
)

class SessionResult(
    val status: SessionProcessor.Status,
    val tFirst: Double,
    val tLast: Double,
    /** UTC epoch seconds of the first sample rounded to the minute (half to even, as Python round). */
    val tStart: Double,
    val duration: Double,
    val fsRaw: Double,
    val fsProbe: Double,
    val fsGrid: Double,
    val nRaw: Long,
    val j50: Long,
    val n50: Long,
    val nSeconds: Int,
    val flaggedSeconds: List<Int>,
    val endSecond: Int?,
    val gMedian: DoubleArray?,
    val gLevel: DoubleArray?,
    val rmsMedian: Double,
    val acceptFraction: Double,
    val bands: Map<Band, BandResult>,
)
