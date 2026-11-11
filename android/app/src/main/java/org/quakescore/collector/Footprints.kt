package org.quakescore.collector

import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.cos
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min

/**
 * Building footprints from the server (GeoJSON FeatureCollection with Polygon or MultiPolygon
 * geometries and properties.id, optional properties.name and properties.addr) and on-device snapping.
 */
object Footprints {
    class Footprint(val id: String, val name: String?, val addr: String?, val polygons: List<List<List<DoubleArray>>>)

    class Candidate(val id: String, val name: String?, val addr: String?, val distanceM: Double) {
        val label: String
            get() {
                val title = listOfNotNull(name, addr).joinToString(", ").ifEmpty { id }
                val d = if (distanceM <= 0.0) "you are inside" else "${distanceM.toInt()} m"
                return "$title\n$id - $d"
            }
    }

    fun parse(geojson: String): List<Footprint> {
        val out = ArrayList<Footprint>()
        val features = JSONObject(geojson).optJSONArray("features") ?: return out
        for (i in 0 until features.length()) {
            val f = features.optJSONObject(i) ?: continue
            val props = f.optJSONObject("properties") ?: JSONObject()
            val id = props.optString("id", "").ifEmpty { f.optString("id", "") }
            if (id.isEmpty()) continue
            val geom = f.optJSONObject("geometry") ?: continue
            val coords = geom.optJSONArray("coordinates") ?: continue
            val polys = when (geom.optString("type")) {
                "Polygon" -> listOf(polygon(coords))
                "MultiPolygon" -> (0 until coords.length()).map { polygon(coords.getJSONArray(it)) }
                else -> continue
            }
            out.add(Footprint(id, props.optString("name", "").ifEmpty { null }, addrOf(props), polys))
        }
        return out
    }

    private fun addrOf(props: JSONObject): String? {
        val a = props.opt("addr") ?: return null
        return when (a) {
            is String -> a.ifEmpty { null }
            is JSONObject -> a.keys().asSequence().map { a.optString(it) }.filter { it.isNotEmpty() }
                .joinToString(" ").ifEmpty { null }
            else -> a.toString()
        }
    }

    private fun polygon(rings: JSONArray): List<List<DoubleArray>> = (0 until rings.length()).map { r ->
        val ring = rings.getJSONArray(r)
        (0 until ring.length()).map { p ->
            val pt = ring.getJSONArray(p)
            doubleArrayOf(pt.getDouble(0), pt.getDouble(1))      // lon, lat
        }
    }

    /** Ranks footprints by distance from (lat, lon): 0 if the point is inside, else distance to the nearest edge. */
    fun rank(fps: List<Footprint>, lat: Double, lon: Double, n: Int = 5): List<Candidate> {
        val ky = 110_540.0
        val kx = 111_320.0 * cos(Math.toRadians(lat))
        fun xy(p: DoubleArray) = doubleArrayOf((p[0] - lon) * kx, (p[1] - lat) * ky)  // metres, origin at the fix
        return fps.map { fp ->
            var inside = false
            var best = Double.MAX_VALUE
            for (poly in fp.polygons) {
                var inPoly = false
                poly.forEachIndexed { ri, ring ->
                    val pts = ring.map(::xy)
                    val hit = contains(pts)
                    if (ri == 0) inPoly = hit else if (hit) inPoly = false   // holes
                    best = min(best, edgeDistance(pts))
                }
                if (inPoly) inside = true
            }
            Candidate(fp.id, fp.name, fp.addr, if (inside) 0.0 else best)
        }.sortedBy { it.distanceM }.take(n)
    }

    /** Ray casting test for the origin. */
    private fun contains(ring: List<DoubleArray>): Boolean {
        var c = false
        var j = ring.size - 1
        for (i in ring.indices) {
            val a = ring[i]
            val b = ring[j]
            if ((a[1] > 0) != (b[1] > 0)) {
                val x = a[0] + (0 - a[1]) * (b[0] - a[0]) / (b[1] - a[1])
                if (x > 0) c = !c
            }
            j = i
        }
        return c
    }

    /** Distance from the origin to the nearest segment of the ring. */
    private fun edgeDistance(ring: List<DoubleArray>): Double {
        var best = Double.MAX_VALUE
        for (i in 0 until ring.size - 1) {
            val a = ring[i]
            val b = ring[i + 1]
            val dx = b[0] - a[0]
            val dy = b[1] - a[1]
            val len2 = dx * dx + dy * dy
            val t = if (len2 > 0) max(0.0, min(1.0, -(a[0] * dx + a[1] * dy) / len2)) else 0.0
            best = min(best, hypot(a[0] + t * dx, a[1] + t * dy))
        }
        if (ring.size == 1) best = hypot(ring[0][0], ring[0][1])
        return best
    }

    /** Great-circle distance in metres (haversine). */
    fun distanceM(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
        val r = 6_371_000.0
        val p1 = Math.toRadians(lat1)
        val p2 = Math.toRadians(lat2)
        val dp = p2 - p1
        val dl = Math.toRadians(lon2 - lon1)
        val h = Math.sin(dp / 2) * Math.sin(dp / 2) + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) * Math.sin(dl / 2)
        return 2 * r * Math.asin(Math.sqrt(min(1.0, h)))
    }
}
