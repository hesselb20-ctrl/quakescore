/* Inline SVG charts for the building detail panel. No chart library. */
(function () {
  "use strict";

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function fmt(x, d) {
    if (x == null || !isFinite(x)) return "–";
    return Number(x).toFixed(d == null ? 1 : d);
  }

  // Colour-blind-safe palettes (ColorBrewer PuOr for diverging/sequential maps, Oranges for damage)
  var SCORE_STOPS = [[0, "#b35806"], [25, "#e08214"], [45, "#fdb863"], [55, "#d8daeb"], [75, "#8073ac"], [100, "#2d004b"]];
  var DAMAGE = [
    { k: "none", label: "None", c: "#f2f2f2" },
    { k: "slight", label: "Slight", c: "#fdd0a2" },
    { k: "moderate", label: "Moderate", c: "#fd8d3c" },
    { k: "extensive", label: "Extensive", c: "#d94801" },
    { k: "complete", label: "Complete", c: "#7f2704" }
  ];

  function lerpHex(a, b, t) {
    var pa = [1, 3, 5].map(function (i) { return parseInt(a.substr(i, 2), 16); });
    var pb = [1, 3, 5].map(function (i) { return parseInt(b.substr(i, 2), 16); });
    return "#" + pa.map(function (v, i) { return Math.round(v + (pb[i] - v) * t).toString(16).padStart(2, "0"); }).join("");
  }
  function rampColor(stops, x) {
    if (x <= stops[0][0]) return stops[0][1];
    for (var i = 1; i < stops.length; i++) {
      if (x <= stops[i][0]) {
        var t = (x - stops[i - 1][0]) / (stops[i][0] - stops[i - 1][0]);
        return lerpHex(stops[i - 1][1], stops[i][1], t);
      }
    }
    return stops[stops.length - 1][1];
  }

  /* Score: measured band and prior-only band on the same 0-100 axis. */
  function scoreBands(s) {
    var W = 320, L = 74, R = 10, x = function (v) { return L + (W - L - R) * v / 100; };
    var rows = [
      { y: 18, label: "Measured", v: s.value, lo: s.lo, hi: s.hi, strong: true },
      { y: 50, label: "Prior only", v: s.prior_value, lo: s.prior_lo, hi: s.prior_hi, strong: false }
    ];
    var out = '<svg class="chart" viewBox="0 0 ' + W + ' 86" role="img" aria-label="' +
      esc("Measured score " + fmt(s.value) + ", band " + fmt(s.lo) + " to " + fmt(s.hi) +
        (s.prior_value != null ? ". Prior-only score " + fmt(s.prior_value) + ", band " + fmt(s.prior_lo) + " to " + fmt(s.prior_hi) : "")) + '">';
    // gradient track shows the colour scale direction
    out += '<defs><linearGradient id="sg" x1="0" x2="1">' + SCORE_STOPS.map(function (st) {
      return '<stop offset="' + st[0] + '%" stop-color="' + st[1] + '"/>';
    }).join("") + "</linearGradient></defs>";
    [0, 25, 50, 75, 100].forEach(function (t) {
      out += '<line class="grid" x1="' + x(t) + '" x2="' + x(t) + '" y1="6" y2="66"/>';
      out += '<text x="' + x(t) + '" y="80" text-anchor="middle">' + t + "</text>";
    });
    rows.forEach(function (r) {
      if (r.v == null) return;
      out += '<text x="0" y="' + (r.y + 4) + '" class="' + (r.strong ? "lbl" : "") + '">' + r.label + "</text>";
      out += '<rect x="' + x(0) + '" y="' + (r.y - 2) + '" width="' + (x(100) - x(0)) + '" height="4" rx="2" fill="url(#sg)" opacity=".35"/>';
      out += '<rect x="' + x(r.lo) + '" y="' + (r.y - 8) + '" width="' + Math.max(2, x(r.hi) - x(r.lo)) + '" height="16" rx="8" fill="' +
        rampColor(SCORE_STOPS, r.v) + '" fill-opacity="' + (r.strong ? 0.85 : 0.35) + '" stroke="currentColor" stroke-opacity=".35"/>';
      out += '<circle cx="' + x(r.v) + '" cy="' + r.y + '" r="5" class="ink" stroke="var(--surface)" stroke-width="2"/>';
    });
    out += "</svg>";
    return out;
  }

  function classBars(probs) {
    var keys = Object.keys(probs || {}).sort(function (a, b) { return probs[b] - probs[a]; });
    return keys.map(function (k) {
      var p = probs[k];
      return '<div style="display:flex;align-items:center;gap:8px;font-size:.84rem;margin:4px 0">' +
        '<span style="width:52px" class="num">' + esc(k) + "</span>" +
        '<span style="flex:1;height:8px;border-radius:4px;background:var(--divider);overflow:hidden">' +
        '<span style="display:block;height:100%;width:' + Math.round(p * 100) + '%;background:var(--accent)"></span></span>' +
        '<span class="num muted" style="width:40px;text-align:right">' + Math.round(p * 100) + "%</span></div>";
    }).join("");
  }

  /* Damage probabilities per scenario. Accepts per-state probabilities (sum <= 1) or exceedance
     probabilities (non-increasing, may sum > 1); exceedance is converted to per-state. */
  function toStates(d) {
    var v = ["slight", "moderate", "extensive", "complete"].map(function (k) { return Math.max(0, +d[k] || 0); });
    var sum = v.reduce(function (a, b) { return a + b; }, 0);
    var nonInc = v[0] >= v[1] && v[1] >= v[2] && v[2] >= v[3];
    if (sum > 1.0001 && nonInc) v = [v[0] - v[1], v[1] - v[2], v[2] - v[3], v[3]];
    sum = v.reduce(function (a, b) { return a + b; }, 0);
    return { none: Math.max(0, 1 - sum), slight: v[0], moderate: v[1], extensive: v[2], complete: v[3] };
  }
  function damageBars(damage) {
    var keys = Object.keys(damage || {});
    var W = 320, L = 74, R = 4, rowH = 26;
    var H = keys.length * rowH + 22;
    var out = '<svg class="chart" viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="Damage state probabilities by scenario">';
    keys.forEach(function (k, i) {
      var st = toStates(damage[k]);
      var y = i * rowH + 4, x0 = L;
      var pga = k.replace("pga_", "");
      out += '<text x="0" y="' + (y + 13) + '" class="lbl">PGA ' + esc(pga) + " g</text>";
      DAMAGE.forEach(function (d) {
        var w = (W - L - R) * st[d.k];
        if (w <= 0) return;
        out += '<rect x="' + x0 + '" y="' + y + '" width="' + w + '" height="18" fill="' + d.c + '"><title>' +
          esc(d.label + ": " + Math.round(st[d.k] * 100) + "%") + "</title></rect>";
        if (w > 26) out += '<text x="' + (x0 + w / 2) + '" y="' + (y + 13) + '" text-anchor="middle" style="fill:' +
          (d.k === "extensive" || d.k === "complete" ? "#fff" : "#1d1d1f") + ';font-size:10px">' + Math.round(st[d.k] * 100) + "</text>";
        x0 += w;
      });
      out += '<rect x="' + L + '" y="' + y + '" width="' + (W - L - R) + '" height="18" rx="3" fill="none" stroke="var(--divider)"/>';
    });
    out += '<text x="' + L + '" y="' + (H - 4) + '">0%</text><text x="' + (W - R) + '" y="' + (H - 4) + '" text-anchor="end">100%</text>';
    out += "</svg>";
    out += '<div class="dmg-legend">' + DAMAGE.map(function (d) { return '<span><i style="background:' + d.c + '"></i>' + d.label + "</span>"; }).join("") + "</div>";
    return out;
  }

  /* Frequency drift: points with +-sigma bars over time. */
  function driftChart(drift) {
    var s = (drift && drift.series) || [];
    if (!s.length) return '<p class="muted small">No frequency series yet.</p>';
    var W = 320, H = 150, L = 46, R = 8, T = 10, B = 26;
    var ts = s.map(function (p) { return Date.parse(p[0]); });
    var lo = Math.min.apply(null, s.map(function (p) { return p[1] - (p[2] || 0); }));
    var hi = Math.max.apply(null, s.map(function (p) { return p[1] + (p[2] || 0); }));
    var pad = (hi - lo) * 0.15 || hi * 0.01 || 0.01; lo -= pad; hi += pad;
    var t0 = Math.min.apply(null, ts), t1 = Math.max.apply(null, ts); if (t1 === t0) t1 = t0 + 864e5;
    var X = function (t) { return L + (W - L - R) * (t - t0) / (t1 - t0); };
    var Y = function (v) { return T + (H - T - B) * (1 - (v - lo) / (hi - lo)); };
    var out = '<svg class="chart" viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="' +
      esc("Fundamental frequency over time, " + s.length + " estimates") + '">';
    for (var i = 0; i <= 3; i++) {
      var v = lo + (hi - lo) * i / 3;
      out += '<line class="grid" x1="' + L + '" x2="' + (W - R) + '" y1="' + Y(v) + '" y2="' + Y(v) + '"/>';
      out += '<text x="' + (L - 6) + '" y="' + (Y(v) + 4) + '" text-anchor="end">' + fmt(v, v < 1 ? 3 : 2) + "</text>";
    }
    out += '<text x="0" y="' + (T + 2) + '" transform="rotate(-90 8 ' + (T + 50) + ')" style="font-size:10px">Hz</text>';
    [0, Math.floor((s.length - 1) / 2), s.length - 1].forEach(function (j, k, arr) {
      if (k > 0 && j === arr[k - 1]) return;
      out += '<text x="' + X(ts[j]) + '" y="' + (H - 8) + '" text-anchor="' + (k === 0 ? "start" : k === 2 ? "end" : "middle") + '">' + esc(s[j][0].slice(0, 7)) + "</text>";
    });
    var path = s.map(function (p, j) { return (j ? "L" : "M") + X(ts[j]).toFixed(1) + " " + Y(p[1]).toFixed(1); }).join(" ");
    out += '<path d="' + path + '" fill="none" stroke="var(--accent)" stroke-width="1.5" stroke-opacity=".6"/>';
    s.forEach(function (p, j) {
      var x = X(ts[j]);
      if (p[2]) out += '<line x1="' + x + '" x2="' + x + '" y1="' + Y(p[1] - p[2]) + '" y2="' + Y(p[1] + p[2]) + '" stroke="var(--accent)" stroke-width="1.5"/>';
      out += '<circle cx="' + x + '" cy="' + Y(p[1]) + '" r="3" fill="var(--accent)"><title>' + esc(p[0] + ": " + fmt(p[1], 3) + " Hz ± " + fmt(p[2], 3)) + "</title></circle>";
    });
    out += "</svg>";
    return out;
  }

  /* Stacked spectrum excess (ratio to the fitted noise baseline) with identified modes marked. */
  function spectrumChart(sp, modes) {
    if (!sp || !sp.f || !sp.f.length) return '<p class="muted small">No spectrum available.</p>';
    var W = 320, H = 170, L = 34, R = 8, T = 18, B = 26;
    var f = sp.f, e = sp.excess;
    var fl = Math.log10(f[0]), fh = Math.log10(f[f.length - 1]);
    var ymax = Math.max.apply(null, e) * 1.08, ymin = Math.min(0, Math.min.apply(null, e));
    var X = function (v) { return L + (W - L - R) * (Math.log10(v) - fl) / (fh - fl); };
    var Y = function (v) { return T + (H - T - B) * (1 - (v - ymin) / (ymax - ymin)); };
    var out = '<svg class="chart" viewBox="0 0 ' + W + " " + H + '" role="img" aria-label="' +
      esc("Stacked spectrum excess in band " + sp.band + " with identified modes marked") + '">';
    var ticks = [];
    for (var d = Math.floor(fl); d <= Math.ceil(fh); d++) [1, 2, 5].forEach(function (m) {
      var v = m * Math.pow(10, d); if (Math.log10(v) >= fl - 1e-9 && Math.log10(v) <= fh + 1e-9) ticks.push(v);
    });
    ticks.forEach(function (v) {
      out += '<line class="grid" x1="' + X(v) + '" x2="' + X(v) + '" y1="' + T + '" y2="' + (H - B) + '"/>';
      out += '<text x="' + X(v) + '" y="' + (H - 12) + '" text-anchor="middle">' + (v < 1 ? v.toFixed(v < 0.1 ? 2 : 1) : v) + "</text>";
    });
    out += '<text x="' + (W - R) + '" y="' + (H - 1) + '" text-anchor="end" style="font-size:10px">Hz (band ' + esc(sp.band) + ")</text>";
    var yt = [ymin, 1, ymax / 1.08].filter(function (v, i, a) { return a.indexOf(v) === i; });
    yt.forEach(function (v) {
      out += '<text x="' + (L - 4) + '" y="' + (Y(v) + 4) + '" text-anchor="end">' + fmt(v, 1) + "</text>";
    });
    out += '<line class="axis" x1="' + L + '" x2="' + (W - R) + '" y1="' + Y(1) + '" y2="' + Y(1) + '" stroke-dasharray="4 3"/>';
    var area = "M" + X(f[0]) + " " + Y(ymin) + " " + f.map(function (v, i) { return "L" + X(v).toFixed(1) + " " + Y(e[i]).toFixed(1); }).join(" ") +
      " L" + X(f[f.length - 1]) + " " + Y(ymin) + " Z";
    out += '<path d="' + area + '" fill="var(--accent)" fill-opacity=".12"/>';
    out += '<path d="' + f.map(function (v, i) { return (i ? "L" : "M") + X(v).toFixed(1) + " " + Y(e[i]).toFixed(1); }).join(" ") +
      '" fill="none" stroke="var(--accent)" stroke-width="1.4"/>';
    (modes || []).forEach(function (m, i) {
      if (m.f < f[0] || m.f > f[f.length - 1]) return;
      var x = X(m.f), ok = m.label === "structural";
      if (m.f_lo != null && m.f_hi != null && ok)
        out += '<rect x="' + X(m.f_lo) + '" y="' + T + '" width="' + Math.max(1, X(m.f_hi) - X(m.f_lo)) + '" height="' + (H - T - B) + '" fill="currentColor" fill-opacity=".08"/>';
      out += '<line x1="' + x + '" x2="' + x + '" y1="' + T + '" y2="' + (H - B) + '" stroke="' + (ok ? "#d55e00" : "var(--secondary)") +
        '" stroke-width="' + (ok ? 1.6 : 1.2) + '"' + (ok ? "" : ' stroke-dasharray="3 3"') + "/>";
      out += '<text x="' + (x + 3) + '" y="' + (ok ? T - 5 : T + 10) + '" style="font-size:10px;fill:' + (ok ? "#d55e00" : "var(--secondary)") + '">' +
        esc(ok ? fmt(m.f, 2) + " Hz" : "×" + fmt(m.f, 1)) + "<title>" + esc(m.label) + "</title></text>";
    });
    out += "</svg>";
    out += '<div class="dmg-legend"><span><i style="background:#d55e00;border-color:#d55e00"></i>Structural mode (shaded: 90% interval)</span><span><i style="background:transparent;border:1px dashed var(--secondary)"></i>Rejected peak</span><span>Dashed line: noise baseline (ratio 1)</span></div>';
    return out;
  }

  window.QSCharts = { esc: esc, fmt: fmt, rampColor: rampColor, SCORE_STOPS: SCORE_STOPS, scoreBands: scoreBands,
    classBars: classBars, damageBars: damageBars, toStates: toStates, driftChart: driftChart, spectrumChart: spectrumChart };
})();
