package org.quakescore.collector

import android.app.AlertDialog
import android.content.Intent
import android.os.Bundle
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

/** Status, setup entry points, "your building" card, and "Delete my contributions and stop". */
class MainActivity : ComponentActivity() {
    private lateinit var prefs: Prefs
    private lateinit var status: TextView
    private lateinit var building: TextView
    private lateinit var card: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = Prefs(this)
        val col = Ui.page(this)
        Ui.title(this, col, "QuakeScore")
        status = Ui.text(this, col, "")
        Ui.heading(this, col, "Your place")
        building = Ui.text(this, col, "")
        Ui.button(this, col, "Choose or confirm building") {
            startActivity(Intent(this, BuildingPickActivity::class.java))
        }
        Ui.button(this, col, "Set floor") {
            startActivity(Intent(this, FloorSetupActivity::class.java))
        }
        Ui.button(this, col, "Settings") {
            startActivity(Intent(this, SettingsActivity::class.java))
        }
        Ui.heading(this, col, "Your building")
        card = Ui.text(this, col, "")
        Ui.spacer(this, col, 24)
        Ui.button(this, col, "Delete my contributions and stop") { confirmDelete() }
    }

    override fun onResume() {
        super.onResume()
        if (!prefs.consent) {
            startActivity(Intent(this, ConsentActivity::class.java))
            return
        }
        if (prefs.setupComplete) RecordingService.start(this)
        render()
        placeCheck()
        loadCard()
    }

    private fun render() {
        val state = when (prefs.serviceState) {
            "recording" -> "Recording now."
            "checking" -> "Checking that the phone is flat and still."
            "waiting" -> "Waiting: records at night with the screen off, the phone flat and still" +
                if (prefs.allowOnBattery) "." else ", while charging."
            else -> if (prefs.setupComplete) "Starting." else "Not running: finish the setup below."
        }
        val pending = SessionStore.pending(this).size
        status.text = buildString {
            append("Opted in. ").append(state).append('\n')
            append("Sessions contributed: ").append(prefs.sessionsContributed)
            if (pending > 0) append(" (").append(pending).append(" waiting to upload)")
            prefs.lastSessionSummary?.let { append("\nLast session: ").append(it) }
        }
        building.text = buildString {
            append("Building: ").append(prefs.buildingName ?: prefs.buildingId ?: "not chosen")
            if (prefs.buildingId != null && prefs.buildingName != null) append(" (").append(prefs.buildingId).append(')')
            append("\nFloor: ")
            val f = prefs.floor
            if (f == null) append("not set") else append(f).append(" (").append(prefs.floorMethod ?: "manual").append(')')
            if (prefs.placeNeedsConfirm) append("\nYou seem to be somewhere else. Confirm your building to resume.")
        }
    }

    /** At most every 12 hours, one foreground fix: more than 150 m from the confirmed place asks again. */
    private fun placeCheck() {
        if (prefs.buildingId == null || !Locations.hasPermission(this)) return
        val now = System.currentTimeMillis()
        if (now - prefs.placeCheckedAtMs < 12 * 3600 * 1000L) return
        prefs.placeCheckedAtMs = now
        Locations.oneFix(this, 30_000) { loc ->
            if (loc == null || prefs.placeLat.isNaN()) return@oneFix
            val d = Footprints.distanceM(prefs.placeLat, prefs.placeLon, loc.latitude, loc.longitude)
            if (d > PLACE_RADIUS_M) {
                prefs.placeNeedsConfirm = true
                render()
            }
        }
    }

    private fun loadCard() {
        val id = prefs.buildingId
        if (id == null) {
            card.text = "Choose your building to see what is known about it."
            return
        }
        card.text = "Loading..."
        val base = prefs.apiBase
        lifecycleScope.launch {
            val text = withContext(Dispatchers.IO) {
                try {
                    val body = Api(base).buildingPublic(id)
                    try {
                        JSONObject(body).toString(2)
                    } catch (e: Exception) {
                        body
                    }
                } catch (e: Exception) {
                    "Nothing to show yet (${e.message ?: "no connection"})."
                }
            }
            card.text = text.take(4000)
        }
    }

    private fun confirmDelete() {
        AlertDialog.Builder(this)
            .setTitle("Delete my contributions and stop")
            .setMessage(
                "This stops all measuring, deletes every stored session on this phone, asks the server to delete " +
                    "every session this phone uploaded, and forgets your building, floor and contributor codes. " +
                    "It cannot be undone.",
            )
            .setPositiveButton("Delete and stop") { _, _ ->
                Contributions.deleteAndStop(this)
                finishAffinity()
            }
            .setNegativeButton("Cancel", null)
            .show()
    }

    companion object {
        const val PLACE_RADIUS_M = 150.0
    }
}
