package org.quakescore.collector

import org.json.JSONObject
import org.quakescore.dsp.Band
import org.quakescore.dsp.Packing
import org.quakescore.dsp.SessionResult
import org.quakescore.dsp.TimeBase

/** Upload schema v1 (android/README.md, docs/platforms.md). */
object SessionJson {
    const val SCHEMA = 1

    fun build(
        sessionId: String,
        buildingId: String,
        contributor: String,
        phoneModel: String,
        sensorName: String,
        floor: Int,
        floorMethod: String,
        result: SessionResult,
        lsb: Double,
        sync: TimeBase.Report,
        tempC: Double?,
        batteryStart: Int,
        batteryEnd: Int,
        charging: Boolean,
        appVersion: String,
    ): JSONObject {
        val o = JSONObject()
        o.put("schema", SCHEMA)
        o.put("session_id", sessionId)
        o.put("building_id", buildingId)
        o.put("contributor", contributor)
        o.put("phone_model", phoneModel)
        o.put("sensor_name", sensorName)
        o.put("floor", floor)
        o.put("floor_method", floorMethod)
        o.put("t_start", result.tStart.toLong())                 // UTC epoch seconds, rounded to the minute
        o.put("duration", finite(result.duration))
        o.put("fs_raw", finite(result.fsRaw))
        o.put("lsb", finite(lsb))
        o.put("sync_source", sync.source)
        o.put("sync_sigma_ms", finite(sync.sigmaMs))
        o.put("accept_fraction", finite(result.acceptFraction))
        o.put("temp_c", tempC ?: JSONObject.NULL)
        o.put("battery_start", batteryStart)
        o.put("battery_end", batteryEnd)
        o.put("charging", charging)
        o.put("platform", "android")
        o.put("app_version", appVersion)
        val bands = JSONObject()
        for (b in arrayOf(Band.L, Band.M, Band.H)) {
            val br = result.bands.getValue(b)
            bands.put(
                b.name,
                JSONObject()
                    .put("k", br.k)
                    .put("csd", Packing.toBase64(br.csd))
                    .put("p4", Packing.toBase64(br.p4)),
            )
        }
        o.put("bands", bands)
        // Tier B sync frames (opt-in) are not part of v1; a future schema 2 would add "frames" here.
        return o
    }

    private fun finite(v: Double): Double = if (v.isFinite()) v else -1.0
}
