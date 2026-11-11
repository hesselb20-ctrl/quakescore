package org.quakescore.collector

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager

class QuakeScoreApp : Application() {
    override fun onCreate() {
        super.onCreate()
        val ch = NotificationChannel(CHANNEL_STATUS, getString(R.string.channel_name), NotificationManager.IMPORTANCE_LOW)
        ch.setShowBadge(false)
        getSystemService(NotificationManager::class.java).createNotificationChannel(ch)
        Prefs(this).installSecret()     // created once, at first start after install
    }

    companion object {
        const val CHANNEL_STATUS = "status"
    }
}
