package org.quakescore.collector

import android.Manifest
import android.os.Build
import android.os.Bundle
import android.widget.Switch
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts

/** Plain-language consent with an explicit opt-in toggle. Nothing runs before the toggle is on. */
class ConsentActivity : ComponentActivity() {

    private val notifPermission = registerForActivityResult(ActivityResultContracts.RequestPermission()) {
        // The service runs either way; without this permission its status notification is hidden.
        finish()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = Prefs(this)
        val col = Ui.page(this)
        Ui.title(this, col, "Help measure how buildings sway")
        Ui.text(
            this, col,
            "QuakeScore uses your phone's motion sensor to measure the tiny, constant swaying of the " +
                "building you sleep in. Many phones together let us estimate how a building would respond to " +
                "an earthquake. It only runs while the phone lies still, by default on a charger at night.",
        )

        Ui.heading(this, col, "What leaves your phone")
        Ui.text(
            this, col,
            "- Vibration summaries: averaged frequency spectra of the motion sensor between about 0.1 and 20 Hz, " +
                "computed on the phone.\n" +
                "- The building you confirm (an id such as osm:way/123) and your floor number, with how it was " +
                "estimated (air pressure or typed in).\n" +
                "- Session start time rounded to the minute, its duration, and how well the phone clock was synchronised.\n" +
                "- Phone model, motion sensor name, its measured sample rate and resolution.\n" +
                "- Battery level at start and end, whether it was charging, and battery temperature.\n" +
                "- A random session id, and a contributor code that is different for each building and is not " +
                "linked to you, your account or your other buildings.",
        )

        Ui.heading(this, col, "What never leaves your phone, or is never collected")
        Ui.text(
            this, col,
            "- No audio. The microphone is never used.\n" +
                "- No motion content above 25 Hz. It is filtered out before anything is kept.\n" +
                "- No raw sensor samples. They exist only briefly in memory, are never stored on the phone and never uploaded.\n" +
                "- Your location is never uploaded. It is used once, on the phone, to find your building. To download " +
                "nearby building outlines the app sends the server an area of roughly 1 km by 1 km (your position " +
                "rounded to 0.01 degrees), not your position.\n" +
                "- No name, email, phone number, contacts, account or advertising id.",
        )

        Ui.heading(this, col, "When it runs")
        Ui.text(
            this, col,
            "Only after you opt in below, inside a night time window you choose, with the screen off, the phone flat " +
                "and still for 2 minutes, and by default only while charging. A session stops when the phone is moved, " +
                "unplugged, or after 8 hours. Uploads happen on Wi-Fi while charging unless you change that. You can " +
                "stop at any time, and \"Delete my contributions and stop\" on the main screen removes everything on " +
                "the phone and asks the server to delete every session this phone uploaded.",
        )

        val toggle = Switch(this).apply {
            text = "I agree to contribute these measurements"
            textSize = 16f
            isChecked = false
        }
        col.addView(toggle)
        val cont = Ui.button(this, col, "Continue") {
            prefs.consent = true
            prefs.installSecret()
            if (Build.VERSION.SDK_INT >= 33) notifPermission.launch(Manifest.permission.POST_NOTIFICATIONS) else finish()
        }
        cont.isEnabled = false
        toggle.setOnCheckedChangeListener { _, on -> cont.isEnabled = on }
        Ui.button(this, col, "Not now") {
            prefs.consent = false
            finishAffinity()
        }
    }
}
