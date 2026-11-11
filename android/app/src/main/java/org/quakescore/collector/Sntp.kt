package org.quakescore.collector

import android.os.SystemClock
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import java.security.SecureRandom

/**
 * Minimal SNTP client (RFC 4330), measuring the offset between UTC and the elapsed-realtime clock,
 * the clock that sensor event timestamps use. Blocking; call it off the main thread.
 */
object Sntp {
    class Sample(
        /** UTC seconds minus elapsed-realtime seconds. */
        val offsetSec: Double,
        /** Round-trip delay minus server processing time, seconds. */
        val delaySec: Double,
        /** Elapsed-realtime seconds at the middle of the exchange. */
        val elapsedSec: Double,
    )

    private const val NTP_PORT = 123
    private const val NTP_UNIX_DELTA = 2_208_988_800L      // seconds from 1900-01-01 to 1970-01-01
    private val rnd = SecureRandom()

    /** One exchange; null on timeout or an invalid reply. */
    fun query(host: String = "pool.ntp.org", timeoutMs: Int = 3000): Sample? = try {
        DatagramSocket().use { socket ->
            socket.soTimeout = timeoutMs
            val addr = InetAddress.getByName(host)
            val req = ByteArray(48)
            req[0] = 0x23                                    // LI 0, version 4, mode 3 (client)
            val nonce = ByteArray(8).also { rnd.nextBytes(it) }
            System.arraycopy(nonce, 0, req, 40, 8)           // transmit timestamp field used as a nonce
            val t1 = SystemClock.elapsedRealtimeNanos()
            socket.send(DatagramPacket(req, req.size, addr, NTP_PORT))
            val buf = ByteArray(48)
            val resp = DatagramPacket(buf, buf.size)
            socket.receive(resp)
            val t4 = SystemClock.elapsedRealtimeNanos()
            parse(buf, resp.length, nonce, t1, t4)
        }
    } catch (e: Exception) {
        null
    }

    /** Best (smallest delay) of several exchanges. */
    fun best(host: String = "pool.ntp.org", tries: Int = 4): Sample? {
        var best: Sample? = null
        repeat(tries) {
            val s = query(host)
            if (s != null && (best == null || s.delaySec < best!!.delaySec)) best = s
        }
        return best
    }

    private fun parse(b: ByteArray, len: Int, nonce: ByteArray, t1: Long, t4: Long): Sample? {
        if (len < 48) return null
        val li = (b[0].toInt() shr 6) and 3
        val mode = b[0].toInt() and 7
        val stratum = b[1].toInt() and 0xff
        if (li == 3 || mode != 4 || stratum !in 1..15) return null
        for (i in 0 until 8) if (b[24 + i] != nonce[i]) return null   // originate must echo our nonce
        val t2 = timestamp(b, 32)        // server receive, UTC seconds
        val t3 = timestamp(b, 40)        // server transmit, UTC seconds
        val e1 = t1 / 1e9
        val e4 = t4 / 1e9
        val offset = ((t2 - e1) + (t3 - e4)) / 2.0
        val delay = (e4 - e1) - (t3 - t2)
        if (delay < 0) return null
        return Sample(offset, delay, (e1 + e4) / 2.0)
    }

    private fun u32(b: ByteArray, o: Int): Long =
        ((b[o].toLong() and 0xff) shl 24) or ((b[o + 1].toLong() and 0xff) shl 16) or
            ((b[o + 2].toLong() and 0xff) shl 8) or (b[o + 3].toLong() and 0xff)

    private fun timestamp(b: ByteArray, o: Int): Double {
        var sec = u32(b, o)
        if ((sec and 0x8000_0000L) == 0L) sec += 1L shl 32       // era 1 (after 2036-02-07), RFC 4330 section 3
        val frac = u32(b, o + 4)
        return (sec - NTP_UNIX_DELTA) + frac / 4_294_967_296.0
    }
}
