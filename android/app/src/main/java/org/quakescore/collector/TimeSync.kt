package org.quakescore.collector

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.LocationManager
import android.os.Build
import android.os.SystemClock
import androidx.core.content.ContextCompat
import org.quakescore.dsp.TimeBase

/**
 * Sync points for TimeBase, in the order of preference of DESIGN.md 3.1 item 2:
 *  1. GNSS time from a GPS fix that the system already has (Location.getTime paired with
 *     Location.getElapsedRealtimeNanos). Only the two time fields are read; the coordinates are not.
 *     The app never requests a fix for this, and it holds no background-location permission, so on
 *     Android 10+ this path normally yields nothing while the screen is off (expected).
 *  2. On Android 13+, SystemClock.currentGnssTimeClock() if the platform keeps GNSS time.
 *  3. SNTP against pool.ntp.org (best of four exchanges), uncertainty = delay / 2.
 * If none works the caller falls back to the wall clock with source "none".
 *
 * The uncertainties given to GNSS points are resolution bounds (1 ms time stamps), not measured
 * accuracies; the actual accuracy is to be measured by comparing against SNTP on a quiet network.
 */
class TimeSync(private val context: Context) {

    fun sample(): TimeBase.SyncPoint? = fromGpsFix() ?: fromGnssClock() ?: fromNtp()

    private fun fromGpsFix(): TimeBase.SyncPoint? {
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION)
            != PackageManager.PERMISSION_GRANTED
        ) return null
        return try {
            val lm = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
            val loc = lm.getLastKnownLocation(LocationManager.GPS_PROVIDER) ?: return null
            val en = loc.elapsedRealtimeNanos
            if (en <= 0L || loc.time <= 0L) return null
            var sigma = 0.0005
            if (Build.VERSION.SDK_INT >= 29 && loc.hasElapsedRealtimeUncertaintyNanos()) {
                sigma += loc.elapsedRealtimeUncertaintyNanos / 1e9
            }
            TimeBase.SyncPoint(en / 1e9, loc.time / 1000.0 - en / 1e9, sigma, "gnss")
        } catch (e: SecurityException) {
            null
        }
    }

    private fun fromGnssClock(): TimeBase.SyncPoint? {
        if (Build.VERSION.SDK_INT < 33) return null
        return try {
            val clock = SystemClock.currentGnssTimeClock()
            val e0 = SystemClock.elapsedRealtimeNanos()
            val ms = clock.millis()
            val e1 = SystemClock.elapsedRealtimeNanos()
            val e = (e0 + e1) / 2e9
            TimeBase.SyncPoint(e, ms / 1000.0 - e, 0.0005 + (e1 - e0) / 2e9, "gnss")
        } catch (e: Exception) {          // DateTimeException when GNSS time is not available
            null
        }
    }

    private fun fromNtp(): TimeBase.SyncPoint? {
        val s = Sntp.best() ?: return null
        return TimeBase.SyncPoint(s.elapsedSec, s.offsetSec, s.delaySec / 2.0, "ntp")
    }

    companion object {
        /** Wall clock against elapsed realtime; quality unknown, reported as sync_source "none". */
        fun wallClockPoint(): TimeBase.SyncPoint {
            val e0 = SystemClock.elapsedRealtimeNanos()
            val ms = System.currentTimeMillis()
            val e = e0 / 1e9
            return TimeBase.SyncPoint(e, ms / 1000.0 - e, Double.NaN, "none")
        }
    }
}
