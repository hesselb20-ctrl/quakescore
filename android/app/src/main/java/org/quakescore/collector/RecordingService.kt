/*
 * Foreground service type: "specialUse".
 *
 * Android 14+ requires every foreground service to declare a type. The candidates for unattended
 * accelerometer collection and why they do not fit:
 *  - "health": meant for fitness and health apps; it requires a health permission (body sensors,
 *    activity recognition or high sampling rate sensors) and a health use case. This is not one.
 *  - "dataSync": meant for transferring data; Android 15 limits it to 6 hours per 24 hours, shorter
 *    than an 8-hour session.
 *  - "location": this service never uses location.
 *  - "connectedDevice": for external devices.
 * The platform's answer for a valid use case that matches no predefined type is "specialUse", with the
 * FOREGROUND_SERVICE_SPECIAL_USE permission and a PROPERTY_SPECIAL_USE_FGS_SUBTYPE text in the manifest
 * that Google Play reviews. It has no time limit.
 *
 * Lifecycle: the service runs while the user is opted in (started from the app or at boot) and shows
 * a low-priority notification. It uses no sensors while waiting. When the conditions hold (setup done,
 * charging unless on-battery is allowed, screen off, inside the night window) it samples the
 * accelerometer at a low rate to check that the phone is flat and still for 2 minutes, then records a
 * session: TYPE_ACCELEROMETER at 5000 us with batching, a partial wake lock held only while
 * recording. A session ends on movement (the dsp-core flagged-run rule), unplugging (unless allowed),
 * or after 8 hours.
 */
package org.quakescore.collector

import android.Manifest
import android.app.Notification
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.hardware.Sensor
import android.hardware.SensorEvent
import android.hardware.SensorEventListener
import android.hardware.SensorManager
import android.os.Build
import android.os.Handler
import android.os.HandlerThread
import android.os.IBinder
import android.os.PowerManager
import android.os.SystemClock
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import org.quakescore.dsp.SessionProcessor
import java.time.LocalTime
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class RecordingService : Service(), SensorEventListener {

    private enum class State { WAITING, PROBING, RECORDING }

    private lateinit var prefs: Prefs
    private lateinit var sm: SensorManager
    private lateinit var pm: PowerManager
    private lateinit var thread: HandlerThread
    private lateinit var handler: Handler
    private val syncExec: ExecutorService = Executors.newSingleThreadExecutor()

    private var accel: Sensor? = null
    private var baro: Sensor? = null
    private var ambient: Sensor? = null
    private var state = State.WAITING
    private var plugged = false
    private var screenOff = false
    private var still: StillnessDetector? = null
    private var recorder: SessionRecorder? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private var nextSyncElapsedMs = Long.MAX_VALUE

    private val receiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            when (intent.action) {
                Intent.ACTION_SCREEN_OFF -> screenOff = true
                Intent.ACTION_SCREEN_ON -> screenOff = false
                Intent.ACTION_POWER_CONNECTED -> plugged = true
                Intent.ACTION_POWER_DISCONNECTED -> plugged = false
            }
            recorder?.onPowerChanged(plugged)
            evaluate()
        }
    }

    private val tick = object : Runnable {
        override fun run() {
            evaluate()
            handler.postDelayed(this, TICK_MS)
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        prefs = Prefs(this)
        startInForeground("Waiting for the night window")
        sm = getSystemService(Context.SENSOR_SERVICE) as SensorManager
        pm = getSystemService(Context.POWER_SERVICE) as PowerManager
        accel = sm.getDefaultSensor(Sensor.TYPE_ACCELEROMETER)
        baro = sm.getDefaultSensor(Sensor.TYPE_PRESSURE)
        ambient = sm.getDefaultSensor(Sensor.TYPE_AMBIENT_TEMPERATURE)
        thread = HandlerThread("quakescore-sensors").apply { start() }
        handler = Handler(thread.looper)
        plugged = Battery.plugged(this)
        screenOff = !pm.isInteractive
        val filter = IntentFilter().apply {
            addAction(Intent.ACTION_SCREEN_OFF)
            addAction(Intent.ACTION_SCREEN_ON)
            addAction(Intent.ACTION_POWER_CONNECTED)
            addAction(Intent.ACTION_POWER_DISCONNECTED)
        }
        ContextCompat.registerReceiver(this, receiver, filter, null, handler, ContextCompat.RECEIVER_NOT_EXPORTED)
        handler.post(tick)
        prefs.serviceState = "waiting"
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (!prefs.consent || accel == null) {
            stopSelf()
            return START_NOT_STICKY
        }
        handler.post { evaluate() }
        return START_STICKY
    }

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        try {
            unregisterReceiver(receiver)
        } catch (e: IllegalArgumentException) {
        }
        sm.unregisterListener(this)
        // A session interrupted by stopping the service is discarded, not uploaded.
        recorder = null
        releaseWakeLock()
        syncExec.shutdown()
        thread.quitSafely()
        prefs.serviceState = "stopped"
        super.onDestroy()
    }

    // ------------------------------------------------------------------ state machine (sensor thread)

    private fun conditionsHold(): Boolean =
        prefs.setupComplete && (plugged || prefs.allowOnBattery) && screenOff && inNightWindow()

    private fun inNightWindow(): Boolean {
        val now = LocalTime.now().let { it.hour * 60 + it.minute }
        val a = prefs.nightStartMin
        val b = prefs.nightEndMin
        return if (a <= b) now in a until b else now >= a || now < b
    }

    private fun evaluate() {
        if (!prefs.consent) {
            stopSelf()
            return
        }
        when (state) {
            State.WAITING -> if (conditionsHold()) startProbe()
            State.PROBING -> if (!conditionsHold()) stopProbe("waiting")
            State.RECORDING -> {
                val r = recorder ?: return
                when {
                    !plugged && !prefs.allowOnBattery -> endSession("unplugging")
                    r.elapsedMs >= MAX_SESSION_MS -> endSession("8-hour limit")
                    SystemClock.elapsedRealtime() >= nextSyncElapsedMs -> {
                        nextSyncElapsedMs += SYNC_INTERVAL_MS
                        requestSync(r)
                    }
                }
            }
        }
    }

    private fun startProbe() {
        val a = accel ?: return
        still = StillnessDetector()
        sm.registerListener(this, a, SensorManager.SENSOR_DELAY_NORMAL, handler)
        state = State.PROBING
        setStatus("checking", "Checking that the phone is flat and still")
    }

    private fun stopProbe(newState: String) {
        accel?.let { sm.unregisterListener(this, it) }
        still = null
        state = State.WAITING
        setStatus(newState, "Waiting for the night window")
    }

    private fun startSession() {
        val a = accel ?: return
        state = State.RECORDING
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "QuakeScore:recording").apply {
            setReferenceCounted(false)
            acquire(MAX_SESSION_MS + 10 * 60 * 1000L)
        }
        val r = SessionRecorder(this, a, prefs)
        recorder = r
        setStatus("recording", "Recording building vibration")
        // Take the first sync point before any sample is mapped to UTC, then start the sensors.
        syncExec.execute {
            val p = TimeSync(this).sample() ?: TimeSync.wallClockPoint()
            handler.post {
                if (recorder !== r) return@post
                r.timeBase.addPoint(p)
                // 5000 us = 200 Hz, the highest rate allowed without HIGH_SAMPLING_RATE_SENSORS; batched.
                sm.registerListener(this, a, SAMPLING_US, MAX_LATENCY_US, handler)
                baro?.let { sm.registerListener(this, it, 1_000_000, MAX_LATENCY_US, handler) }
                ambient?.let { sm.registerListener(this, it, 1_000_000, MAX_LATENCY_US, handler) }
                nextSyncElapsedMs = SystemClock.elapsedRealtime() + SYNC_INTERVAL_MS
            }
        }
    }

    private fun requestSync(r: SessionRecorder) {
        syncExec.execute {
            val p = TimeSync(this).sample() ?: return@execute
            r.timeBase.addPoint(p)            // synchronized; takes effect at the next mapped sample
        }
    }

    private fun endSession(reason: String) {
        val r = recorder ?: return
        recorder = null
        sm.unregisterListener(this)
        state = State.WAITING
        nextSyncElapsedMs = Long.MAX_VALUE
        val result = r.processor.finish()
        setStatus("waiting", "Waiting for the night window")
        syncExec.execute {
            // Final sync point: improves the reported fit; samples were already mapped.
            TimeSync(this).sample()?.let { r.timeBase.addPoint(it) }
            try {
                val json = r.buildUpload(result, reason)
                if (json != null) {
                    SessionStore.write(applicationContext, r.sessionId, json)
                    UploadWorker.enqueue(applicationContext)
                }
            } finally {
                handler.post { releaseWakeLock() }
            }
        }
    }

    private fun releaseWakeLock() {
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
    }

    // ------------------------------------------------------------------ sensors

    override fun onSensorChanged(event: SensorEvent) {
        val type = event.sensor.type
        if (type == Sensor.TYPE_PRESSURE) {
            recorder?.onPressure(event.values[0])
            return
        }
        if (type == Sensor.TYPE_AMBIENT_TEMPERATURE) {
            recorder?.onAmbientTemperature(event.values[0])
            return
        }
        if (type != Sensor.TYPE_ACCELEROMETER) return
        if (state == State.PROBING) {
            if (still?.add(event) == true) {
                stopProbe("checking")
                if (conditionsHold()) startSession()
            }
        } else if (state == State.RECORDING) {
            val r = recorder ?: return
            if (!r.timeBase.hasPoints) return
            r.onAccel(event)
            val abort = r.abortReason
            if (abort != null) {
                endSession(abort)
            } else if (r.processor.ended) {
                endSession(if (r.processor.status == SessionProcessor.Status.NOT_FLAT) "not flat" else "movement")
            }
        }
    }

    override fun onAccuracyChanged(sensor: Sensor?, accuracy: Int) {}

    // ------------------------------------------------------------------ notification

    private fun buildNotification(text: String): Notification {
        val pi = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        return NotificationCompat.Builder(this, QuakeScoreApp.CHANNEL_STATUS)
            .setSmallIcon(R.drawable.ic_stat_quake)
            .setContentTitle("QuakeScore")
            .setContentText(text)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setContentIntent(pi)
            .build()
    }

    private fun startInForeground(text: String) {
        val n = buildNotification(text)
        if (Build.VERSION.SDK_INT >= 34) {
            startForeground(NOTIFICATION_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE)
        } else {
            startForeground(NOTIFICATION_ID, n)
        }
    }

    private fun setStatus(state: String, text: String) {
        prefs.serviceState = state
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) return
        getSystemService(NotificationManager::class.java).notify(NOTIFICATION_ID, buildNotification(text))
    }

    companion object {
        private const val NOTIFICATION_ID = 1
        private const val TICK_MS = 30_000L
        private const val SYNC_INTERVAL_MS = 10 * 60 * 1000L
        const val MAX_SESSION_MS = 8 * 3600 * 1000L
        private const val SAMPLING_US = 5000
        private const val MAX_LATENCY_US = 10_000_000      // 10 s batching; the FIFO may force earlier delivery

        fun start(ctx: Context) {
            ContextCompat.startForegroundService(ctx, Intent(ctx, RecordingService::class.java))
        }

        fun stop(ctx: Context) {
            ctx.stopService(Intent(ctx, RecordingService::class.java))
        }
    }
}
