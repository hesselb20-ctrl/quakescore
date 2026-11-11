package org.quakescore.collector

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** Restarts the waiting service after a reboot, only if the user has opted in and finished setup. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        if (Prefs(context).setupComplete) RecordingService.start(context)
    }
}
