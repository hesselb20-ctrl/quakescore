package org.quakescore.collector

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.os.CancellationSignal
import android.os.Handler
import android.os.Looper
import androidx.core.content.ContextCompat

/**
 * One location fix, requested in the foreground only (building pick, and the place check when the
 * app is opened). The result never leaves the device; see README "Building pick".
 */
object Locations {
    fun hasPermission(ctx: Context): Boolean =
        ContextCompat.checkSelfPermission(ctx, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(ctx, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED

    /** Calls back on the main thread with a fix, or null after timeoutMs or if no provider is enabled. */
    @SuppressLint("MissingPermission")
    fun oneFix(ctx: Context, timeoutMs: Long, cb: (Location?) -> Unit) {
        val main = Handler(Looper.getMainLooper())
        if (!hasPermission(ctx)) {
            main.post { cb(null) }
            return
        }
        val lm = ctx.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        val fine = ContextCompat.checkSelfPermission(ctx, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        val provider = when {
            Build.VERSION.SDK_INT >= 31 && lm.allProviders.contains(LocationManager.FUSED_PROVIDER) &&
                lm.isProviderEnabled(LocationManager.FUSED_PROVIDER) -> LocationManager.FUSED_PROVIDER
            fine && lm.isProviderEnabled(LocationManager.GPS_PROVIDER) -> LocationManager.GPS_PROVIDER
            lm.isProviderEnabled(LocationManager.NETWORK_PROVIDER) -> LocationManager.NETWORK_PROVIDER
            else -> null
        }
        if (provider == null) {
            main.post { cb(null) }
            return
        }
        var done = false
        val finish: (Location?) -> Unit = { l ->
            if (!done) {
                done = true
                cb(l)
            }
        }
        if (Build.VERSION.SDK_INT >= 30) {
            val cancel = CancellationSignal()
            lm.getCurrentLocation(provider, cancel, ctx.mainExecutor) { l -> finish(l) }
            main.postDelayed({
                cancel.cancel()
                finish(null)
            }, timeoutMs)
        } else {
            val listener = object : LocationListener {
                override fun onLocationChanged(location: Location) {
                    lm.removeUpdates(this)
                    finish(location)
                }

                // Implemented explicitly: these are abstract on API 26-29.
                @Deprecated("Deprecated in Java")
                override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
                override fun onProviderEnabled(provider: String) {}
                override fun onProviderDisabled(provider: String) {}
            }
            @Suppress("DEPRECATION")
            lm.requestSingleUpdate(provider, listener, Looper.getMainLooper())
            main.postDelayed({
                lm.removeUpdates(listener)
                finish(null)
            }, timeoutMs)
        }
    }
}
