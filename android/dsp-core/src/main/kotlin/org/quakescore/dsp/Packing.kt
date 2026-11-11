package org.quakescore.dsp

import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.Base64

/** Upload packing (schema v1): little-endian float32 arrays as standard base64 with padding. */
object Packing {
    fun toBase64(values: FloatArray): String {
        val bb = ByteBuffer.allocate(values.size * 4).order(ByteOrder.LITTLE_ENDIAN)
        bb.asFloatBuffer().put(values)
        return Base64.getEncoder().encodeToString(bb.array())
    }

    fun fromBase64(text: String): FloatArray {
        val bytes = Base64.getDecoder().decode(text)
        require(bytes.size % 4 == 0) { "length is not a multiple of 4" }
        val fb = ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer()
        val out = FloatArray(fb.remaining())
        fb.get(out)
        return out
    }
}
