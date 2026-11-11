package org.quakescore.collector

import android.app.Activity
import android.graphics.Typeface
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/** Small helpers for the plain-View screens (no XML layouts). */
object Ui {
    fun dp(a: Activity, v: Int): Int = (v * a.resources.displayMetrics.density).toInt()

    /** A scrolling vertical column set as the activity content. */
    fun page(a: Activity): LinearLayout {
        val col = LinearLayout(a).apply {
            orientation = LinearLayout.VERTICAL
            val p = dp(a, 16)
            setPadding(p, p, p, p)
        }
        val sv = ScrollView(a).apply { addView(col, ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)) }
        sv.fitsSystemWindows = true
        a.setContentView(sv)
        return col
    }

    fun title(a: Activity, parent: LinearLayout, s: String): TextView = text(a, parent, s, 22f).apply {
        setTypeface(typeface, Typeface.BOLD)
    }

    fun heading(a: Activity, parent: LinearLayout, s: String): TextView = text(a, parent, s, 18f).apply {
        setTypeface(typeface, Typeface.BOLD)
        setPadding(0, dp(a, 12), 0, dp(a, 4))
    }

    fun text(a: Activity, parent: LinearLayout, s: String, sizeSp: Float = 16f): TextView {
        val t = TextView(a).apply {
            text = s
            textSize = sizeSp
            setPadding(0, dp(a, 4), 0, dp(a, 4))
        }
        parent.addView(t)
        return t
    }

    fun button(a: Activity, parent: LinearLayout, label: String, onClick: () -> Unit): Button {
        val b = Button(a).apply {
            text = label
            isAllCaps = false
            setOnClickListener { onClick() }
        }
        parent.addView(b, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        return b
    }

    fun spacer(a: Activity, parent: LinearLayout, heightDp: Int = 12) {
        parent.addView(View(a), LinearLayout.LayoutParams(1, dp(a, heightDp)))
    }
}
