package org.quakescore.collector

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.location.Location
import android.os.Bundle
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ListView
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlin.math.round

/**
 * Building pick (DESIGN.md 3.2): one location fix, used on the device only. The server receives the
 * position rounded to 0.01 degrees and returns the footprints around it; the phone snaps to the nearest
 * footprint and shows the five nearest for the user to confirm. Only the building id is uploaded later.
 */
class BuildingPickActivity : ComponentActivity() {
    private lateinit var prefs: Prefs
    private lateinit var info: TextView
    private lateinit var list: ListView
    private lateinit var confirm: Button
    private var candidates: List<Footprints.Candidate> = emptyList()
    private var fix: Location? = null

    private val permission = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { granted ->
        if (granted.values.any { it }) locate() else showMessage("Location permission is needed once to find your building.")
    }

    private fun showMessage(s: String) {
        info.text = s
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = Prefs(this)
        val col = Ui.page(this)
        Ui.title(this, col, "Your building")
        Ui.text(
            this, col,
            "Stand in or next to the building where the phone will rest. The app takes one location fix, keeps it " +
                "on this phone, and asks the server only for building outlines in the surrounding ~1 km square.",
        )
        info = Ui.text(this, col, "")
        list = ListView(this).apply { choiceMode = ListView.CHOICE_MODE_SINGLE }
        col.addView(list, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, Ui.dp(this, 360)))
        confirm = Ui.button(this, col, "Confirm this building") { confirmSelection() }
        confirm.isEnabled = false
        list.setOnItemClickListener { _, _, _, _ -> confirm.isEnabled = true }
        Ui.button(this, col, "Try again") { start() }
        start()
    }

    private fun start() {
        confirm.isEnabled = false
        if (Locations.hasPermission(this)) {
            locate()
        } else {
            permission.launch(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION))
        }
    }

    private fun locate() {
        info.text = "Getting one location fix..."
        Locations.oneFix(this, 30_000) { loc ->
            if (loc == null) {
                info.text = "No location fix. Check that location is on, then try again."
                return@oneFix
            }
            fix = loc
            fetch(loc)
        }
    }

    private fun fetch(loc: Location) {
        val precise = ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) ==
            PackageManager.PERMISSION_GRANTED
        info.text = "Looking up nearby buildings..."
        val lat = round(loc.latitude * 100.0) / 100.0
        val lon = round(loc.longitude * 100.0) / 100.0
        val base = prefs.apiBase
        lifecycleScope.launch {
            val ranked = withContext(Dispatchers.IO) {
                try {
                    Footprints.rank(Footprints.parse(Api(base).footprints(lat, lon)), loc.latitude, loc.longitude)
                } catch (e: Exception) {
                    null
                }
            }
            if (ranked == null) {
                info.text = "Could not reach the server. Try again later."
                return@launch
            }
            candidates = ranked
            if (ranked.isEmpty()) {
                info.text = "No buildings found here. Move closer to your building and try again."
                return@launch
            }
            val known = prefs.buildingId
            val near = !prefs.placeLat.isNaN() &&
                Footprints.distanceM(prefs.placeLat, prefs.placeLon, loc.latitude, loc.longitude) <= MainActivity.PLACE_RADIUS_M
            info.text = buildString {
                append("Pick your building (nearest first).")
                if (!precise) append(" Precise location was not granted, so the list may not contain your building.")
                if (known != null && near) append(" Your confirmed building is marked if it is in the list.")
            }
            list.adapter = ArrayAdapter(this@BuildingPickActivity, android.R.layout.simple_list_item_single_choice,
                ranked.map { it.label })
            val idx = ranked.indexOfFirst { it.id == known }
            if (idx >= 0 && near) {
                list.setItemChecked(idx, true)
                confirm.isEnabled = true
            }
        }
    }

    private fun confirmSelection() {
        val pos = list.checkedItemPosition
        val loc = fix ?: return
        if (pos < 0 || pos >= candidates.size) return
        val c = candidates[pos]
        val changed = c.id != prefs.buildingId
        prefs.buildingId = c.id
        prefs.buildingName = c.name ?: c.addr
        // Stored on the phone only, rounded to about 10 m, for the 150 m place check.
        prefs.placeLat = round(loc.latitude * 1e4) / 1e4
        prefs.placeLon = round(loc.longitude * 1e4) / 1e4
        prefs.placeCheckedAtMs = System.currentTimeMillis()
        prefs.placeNeedsConfirm = false
        if (changed) {
            prefs.floor = null
            prefs.floorMethod = null
            startActivity(Intent(this, FloorSetupActivity::class.java))
        }
        finish()
    }
}
