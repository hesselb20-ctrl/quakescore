package org.quakescore.dsp

import kotlin.math.sqrt

internal object Vec3 {
    fun norm(v: DoubleArray): Double = sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])

    fun cross(a: DoubleArray, b: DoubleArray): DoubleArray = doubleArrayOf(
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )
}

object Levelling {
    /**
     * pipeline.level_rotation: rows are the level-frame axes in the device frame, z along gravity,
     * x the projection of the device x axis onto the horizontal plane, y = z cross x.
     */
    fun rotation(g: DoubleArray): Array<DoubleArray> {
        val gn = Vec3.norm(g)
        val z = DoubleArray(3) { g[it] / gn }
        val x = doubleArrayOf(1.0 - z[0] * z[0], 0.0 - z[0] * z[1], 0.0 - z[0] * z[2])
        val xn = Vec3.norm(x)
        for (i in 0 until 3) x[i] /= xn
        return arrayOf(x, Vec3.cross(z, x), z)
    }
}

internal object Stats {
    /** numpy.median: middle value, or the mean of the two middle values for an even count. */
    fun median(values: DoubleArray, n: Int = values.size): Double {
        require(n > 0)
        val s = values.copyOf(n)
        s.sort()
        return if (n % 2 == 1) s[n / 2] else (s[n / 2 - 1] + s[n / 2]) / 2.0
    }
}
