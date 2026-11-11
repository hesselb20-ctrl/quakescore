package org.quakescore.collector

import android.content.Context
import android.content.SharedPreferences
import android.util.Base64
import java.security.MessageDigest
import java.security.SecureRandom

/**
 * App-private settings and state. Everything here stays on the device. The install secret is never
 * uploaded; only the per-building contributor hash derived from it is.
 */
class Prefs(context: Context) {
    private val sp: SharedPreferences = context.applicationContext.getSharedPreferences("qs", Context.MODE_PRIVATE)

    var consent: Boolean
        get() = sp.getBoolean("consent", false)
        set(v) = sp.edit().putBoolean("consent", v).apply()

    // ---- settings
    var nightStartMin: Int
        get() = sp.getInt("night_start", 23 * 60)
        set(v) = sp.edit().putInt("night_start", v).apply()
    var nightEndMin: Int
        get() = sp.getInt("night_end", 7 * 60)
        set(v) = sp.edit().putInt("night_end", v).apply()
    var allowOnBattery: Boolean
        get() = sp.getBoolean("allow_battery", false)
        set(v) = sp.edit().putBoolean("allow_battery", v).apply()
    var uploadOnMetered: Boolean
        get() = sp.getBoolean("upload_metered", false)
        set(v) = sp.edit().putBoolean("upload_metered", v).apply()
    var uploadRequiresCharging: Boolean
        get() = sp.getBoolean("upload_charging", true)
        set(v) = sp.edit().putBoolean("upload_charging", v).apply()
    var apiBase: String
        get() = sp.getString("api_base", null) ?: BuildConfig.API_BASE
        set(v) = sp.edit().putString("api_base", v.trimEnd('/')).apply()

    // ---- building and place (the fix is kept on the device only, for the 150 m place check)
    var buildingId: String?
        get() = sp.getString("building_id", null)
        set(v) = sp.edit().putString("building_id", v).apply()
    var buildingName: String?
        get() = sp.getString("building_name", null)
        set(v) = sp.edit().putString("building_name", v).apply()
    var placeLat: Double
        get() = java.lang.Double.longBitsToDouble(sp.getLong("place_lat", java.lang.Double.doubleToLongBits(Double.NaN)))
        set(v) = sp.edit().putLong("place_lat", java.lang.Double.doubleToLongBits(v)).apply()
    var placeLon: Double
        get() = java.lang.Double.longBitsToDouble(sp.getLong("place_lon", java.lang.Double.doubleToLongBits(Double.NaN)))
        set(v) = sp.edit().putLong("place_lon", java.lang.Double.doubleToLongBits(v)).apply()
    var placeCheckedAtMs: Long
        get() = sp.getLong("place_checked", 0L)
        set(v) = sp.edit().putLong("place_checked", v).apply()
    /** True when a later fix was more than 150 m from the confirmed place; recording waits for a new confirmation. */
    var placeNeedsConfirm: Boolean
        get() = sp.getBoolean("place_confirm", false)
        set(v) = sp.edit().putBoolean("place_confirm", v).apply()

    // ---- floor
    var floor: Int?
        get() = if (sp.contains("floor")) sp.getInt("floor", 0) else null
        set(v) = sp.edit().apply { if (v == null) remove("floor") else putInt("floor", v) }.apply()
    var floorMethod: String?
        get() = sp.getString("floor_method", null)
        set(v) = sp.edit().putString("floor_method", v).apply()
    /** Height above the entrance from the setup measurement, metres (kept with the estimate). */
    var floorDh: Double
        get() = sp.getFloat("floor_dh", Float.NaN).toDouble()
        set(v) = sp.edit().putFloat("floor_dh", v.toFloat()).apply()
    var pGroundHpa: Double
        get() = sp.getFloat("p_ground", Float.NaN).toDouble()
        set(v) = sp.edit().putFloat("p_ground", v.toFloat()).apply()
    var pGroundAtMs: Long
        get() = sp.getLong("p_ground_at", 0L)
        set(v) = sp.edit().putLong("p_ground_at", v).apply()

    // ---- status
    var sessionsContributed: Int
        get() = sp.getInt("sessions", 0)
        set(v) = sp.edit().putInt("sessions", v).apply()
    var uploadedIds: Set<String>
        get() = sp.getStringSet("uploaded", emptySet())!!.toSet()
        set(v) = sp.edit().putStringSet("uploaded", v).apply()
    var serviceState: String
        get() = sp.getString("state", "stopped")!!
        set(v) = sp.edit().putString("state", v).apply()
    var lastSessionSummary: String?
        get() = sp.getString("last_summary", null)
        set(v) = sp.edit().putString("last_summary", v).apply()

    val setupComplete: Boolean
        get() = consent && buildingId != null && floor != null && !placeNeedsConfirm

    /** 32 random bytes created on first use (first start after install) and never uploaded. */
    fun installSecret(): ByteArray {
        val existing = sp.getString("install_secret", null)
        if (existing != null) return Base64.decode(existing, Base64.NO_WRAP)
        val b = ByteArray(32).also { SecureRandom().nextBytes(it) }
        sp.edit().putString("install_secret", Base64.encodeToString(b, Base64.NO_WRAP)).apply()
        return b
    }

    /** First 16 hex characters of SHA-256(install_secret || building_id). */
    fun contributor(buildingId: String): String {
        val md = MessageDigest.getInstance("SHA-256")
        md.update(installSecret())
        md.update(buildingId.toByteArray(Charsets.UTF_8))
        return md.digest().joinToString("") { "%02x".format(it.toInt() and 0xff) }.substring(0, 16)
    }

    /** Removes everything, including the install secret, so a later opt-in gets new pseudonyms. */
    fun wipe() {
        sp.edit().clear().apply()
    }
}
