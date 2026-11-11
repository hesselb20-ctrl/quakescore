package org.quakescore.dsp

/** Window length, hop and number of one-sided bins (quakescore/features.py). */
const val NFFT = 2048
const val HOP = NFFT / 2
const val NBINS = NFFT / 2 + 1

/** Zoom bands and their sample rates (quakescore/features.py BANDS). */
enum class Band(val fs: Double) {
    L(3.125),
    M(12.5),
    H(50.0),
}

/**
 * Streaming parameters. The gate values equal quakescore.device.pipeline.DeviceConfig; the warm-up,
 * rate-probe and flagged-run values are the streaming rules described in SessionProcessor.kt and
 * mirrored by experiments/export_device_vectors.py (process_session_streaming).
 */
data class StreamConfig(
    val warmupSeconds: Int = 120,
    val rateProbeSeconds: Double = 10.0,
    val maxFlaggedRun: Int = 60,
    val gateRmsFactor: Double = 5.0,
    val gateTilt: Double = 0.0035,
    val flatCos: Double = 0.966,
)

/** Receives one three-axis sample at an absolute (epoch-anchored) sample index. */
fun interface Sink3 {
    fun accept(index: Long, x: Double, y: Double, z: Double)
}
