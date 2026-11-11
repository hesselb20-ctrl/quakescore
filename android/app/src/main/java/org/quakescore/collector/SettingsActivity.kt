package org.quakescore.collector

import android.os.Bundle
import android.text.InputType
import android.widget.EditText
import android.widget.Switch
import androidx.activity.ComponentActivity
import java.util.Locale

class SettingsActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = Prefs(this)
        val col = Ui.page(this)
        Ui.title(this, col, "Settings")
        val info = Ui.text(this, col, "")

        Ui.heading(this, col, "Night window (24 h clock, HH:MM)")
        val start = timeField(prefs.nightStartMin)
        val end = timeField(prefs.nightEndMin)
        Ui.text(this, col, "Start")
        col.addView(start)
        Ui.text(this, col, "End")
        col.addView(end)

        Ui.heading(this, col, "Recording")
        val battery = switch("Also record when not charging (uses battery)", prefs.allowOnBattery)
        col.addView(battery)

        Ui.heading(this, col, "Upload")
        val metered = switch("Allow upload on mobile data", prefs.uploadOnMetered)
        val charging = switch("Upload only while charging", prefs.uploadRequiresCharging)
        col.addView(metered)
        col.addView(charging)

        Ui.heading(this, col, "Server")
        val base = EditText(this).apply {
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            setText(prefs.apiBase)
        }
        col.addView(base)

        Ui.button(this, col, "Save") {
            val a = parse(start.text.toString())
            val b = parse(end.text.toString())
            val url = base.text.toString().trim()
            if (a == null || b == null || a == b) {
                info.text = "Enter start and end as HH:MM, and make them different."
            } else if (!url.startsWith("https://")) {
                info.text = "The server address must start with https://"
            } else {
                prefs.nightStartMin = a
                prefs.nightEndMin = b
                prefs.allowOnBattery = battery.isChecked
                prefs.uploadOnMetered = metered.isChecked
                prefs.uploadRequiresCharging = charging.isChecked
                prefs.apiBase = url
                if (SessionStore.pending(this).isNotEmpty()) UploadWorker.enqueue(this)
                finish()
            }
        }
    }

    private fun timeField(min: Int): EditText = EditText(this).apply {
        inputType = InputType.TYPE_CLASS_DATETIME or InputType.TYPE_DATETIME_VARIATION_TIME
        setText(String.format(Locale.ROOT, "%02d:%02d", min / 60, min % 60))
    }

    private fun switch(label: String, value: Boolean): Switch = Switch(this).apply {
        text = label
        textSize = 16f
        isChecked = value
    }

    private fun parse(s: String): Int? {
        val p = s.trim().split(":")
        if (p.size != 2) return null
        val h = p[0].toIntOrNull() ?: return null
        val m = p[1].toIntOrNull() ?: return null
        if (h !in 0..23 || m !in 0..59) return null
        return h * 60 + m
    }
}
