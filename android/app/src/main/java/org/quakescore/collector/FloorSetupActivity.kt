package org.quakescore.collector

import android.hardware.Sensor
import android.os.Bundle
import android.text.InputType
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.activity.ComponentActivity
import java.util.Locale

/**
 * Floor (DESIGN.md 3.2). With a barometer: pressure at the entrance (ground level), then at the spot
 * where the phone will rest; floor = round(dh / 3.2 m), method "baro_entry". Without one, or if the
 * user prefers, manual entry, method "manual". Both the estimate and the method are kept.
 */
class FloorSetupActivity : ComponentActivity() {
    private lateinit var prefs: Prefs
    private lateinit var info: TextView
    private lateinit var useBaro: Button
    private var estimate: Pair<Int, Double>? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prefs = Prefs(this)
        val col = Ui.page(this)
        Ui.title(this, col, "Your floor")
        info = Ui.text(this, col, "")

        if (Floor.hasBarometer(this)) {
            Ui.text(
                this, col,
                "1. Go to the entrance of the building (ground level) and tap the first button. Hold still for 10 s.\n" +
                    "2. Go to the place where the phone will rest at night and tap the second button.",
            )
            lateinit var atSpot: Button
            Ui.button(this, col, "I am at the entrance (ground level)") {
                info.text = "Measuring air pressure for 10 s..."
                Floor.medianReading(this, Sensor.TYPE_PRESSURE, 10_000) { p ->
                    if (p == null) {
                        info.text = "The barometer gave no reading. Enter the floor below."
                    } else {
                        prefs.pGroundHpa = p
                        prefs.pGroundAtMs = System.currentTimeMillis()
                        info.text = String.format(Locale.ROOT, "Entrance: %.2f hPa. Now go to the resting spot.", p)
                        atSpot.isEnabled = true
                    }
                }
            }
            atSpot = Ui.button(this, col, "I am at the spot where the phone will rest") { measureSpot() }
            atSpot.isEnabled = prefs.pGroundHpa.isFinite()
            useBaro = Ui.button(this, col, "Use this floor") {
                val e = estimate ?: return@button
                prefs.floor = e.first
                prefs.floorMethod = "baro_entry"
                prefs.floorDh = e.second
                finish()
            }
            useBaro.isEnabled = false
        } else {
            Ui.text(this, col, "This phone has no barometer, so please enter your floor.")
        }

        Ui.heading(this, col, "Or enter the floor yourself")
        Ui.text(this, col, "Ground floor is 0, the floor above it 1, basements negative.")
        val field = EditText(this).apply {
            inputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_SIGNED
            prefs.floor?.let { setText(it.toString()) }
        }
        col.addView(field)
        Ui.button(this, col, "Save floor") {
            val n = field.text.toString().trim().toIntOrNull()
            if (n == null || n < -5 || n > 200) {
                info.text = "Enter a whole number."
            } else {
                prefs.floor = n
                prefs.floorMethod = "manual"
                prefs.floorDh = Double.NaN
                finish()
            }
        }
    }

    private fun measureSpot() {
        info.text = "Measuring air pressure for 10 s..."
        Floor.medianReading(this, Sensor.TYPE_PRESSURE, 10_000) { p ->
            if (p == null) {
                info.text = "The barometer gave no reading. Enter the floor below."
                return@medianReading
            }
            Floor.medianReading(this, Sensor.TYPE_AMBIENT_TEMPERATURE, 3_000) { t ->
                val dh = Floor.heightM(prefs.pGroundHpa, p, t)
                val f = Floor.floorOf(dh)
                estimate = f to dh
                info.text = String.format(
                    Locale.ROOT,
                    "Height above the entrance: %.1f m, so floor %d (assuming %.1f m per storey). " +
                        "If that is wrong, enter the floor below.",
                    dh, f, Floor.STOREY_M,
                )
                useBaro.isEnabled = true
            }
        }
    }
}
