/* Portfolio panel. Live mode posts the CSV to POST /v1/portfolio. Static mode matches in the
   browser on building_id and lat/lon only (point in polygon, else nearest footprint within 30 m). */
(function () {
  "use strict";
  var C = window.QSCharts, esc = C.esc, fmt = C.fmt;
  var NEAREST_M = 30;

  function parseCSV(text) {
    var rows = [], row = [], cell = "", q = false;
    text = text.replace(/^﻿/, "");
    for (var i = 0; i < text.length; i++) {
      var ch = text[i];
      if (q) {
        if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++; }
        else if (ch === '"') q = false;
        else cell += ch;
      } else if (ch === '"') q = true;
      else if (ch === ",") { row.push(cell); cell = ""; }
      else if (ch === "\n" || ch === "\r") {
        if (ch === "\r" && text[i + 1] === "\n") i++;
        row.push(cell); rows.push(row); row = []; cell = "";
      } else cell += ch;
    }
    if (cell !== "" || row.length) { row.push(cell); rows.push(row); }
    return rows.filter(function (r) { return r.some(function (c) { return c.trim() !== ""; }); });
  }

  var ALIASES = { building_id: ["building_id", "buildingid", "quakescore_id"], lat: ["lat", "latitude", "y"],
    lon: ["lon", "lng", "long", "longitude", "x"], address: ["address", "addr", "street_address"],
    ref: ["ref", "asset_id", "id", "name", "reference"] };

  function rowsFromCSV(text) {
    var rows = parseCSV(text);
    if (!rows.length) throw new Error("The file is empty.");
    var h = rows[0].map(function (c) { return c.trim().toLowerCase().replace(/ /g, "_"); });
    var idx = {};
    Object.keys(ALIASES).forEach(function (k) {
      idx[k] = -1;
      ALIASES[k].some(function (a) { var j = h.indexOf(a); if (j >= 0) { idx[k] = j; return true; } return false; });
    });
    if (idx.building_id < 0 && idx.address < 0 && (idx.lat < 0 || idx.lon < 0))
      throw new Error("The CSV needs a building_id column, lat and lon columns, or an address column.");
    return rows.slice(1).map(function (r) {
      var o = {};
      Object.keys(idx).forEach(function (k) { var v = idx[k] >= 0 ? (r[idx[k]] || "").trim() : ""; o[k] = v || null; });
      return o;
    });
  }

  // --- geometry (same rules as quakescore/service/geo.py) ---
  function rings(g) { return g.type === "Polygon" ? [g.coordinates] : g.type === "MultiPolygon" ? g.coordinates : []; }
  function inRing(x, y, r) {
    var inside = false;
    for (var i = 0, j = r.length - 1; i < r.length; j = i++) {
      var xi = r[i][0], yi = r[i][1], xj = r[j][0], yj = r[j][1];
      if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }
  function contains(g, lat, lon) {
    return rings(g).some(function (p) { return inRing(lon, lat, p[0]) && !p.slice(1).some(function (h) { return inRing(lon, lat, h); }); });
  }
  function segDist(ax, ay, bx, by) {
    var dx = bx - ax, dy = by - ay, L = dx * dx + dy * dy;
    var t = L === 0 ? 0 : Math.max(0, Math.min(1, -(ax * dx + ay * dy) / L));
    return Math.hypot(ax + t * dx, ay + t * dy);
  }
  function distM(g, lat, lon) {
    if (g.type === "Point") {
      var kx0 = 111320 * Math.cos(lat * Math.PI / 180);
      return Math.hypot((g.coordinates[0] - lon) * kx0, (g.coordinates[1] - lat) * 111320);
    }
    if (contains(g, lat, lon)) return 0;
    var kx = 111320 * Math.cos(lat * Math.PI / 180), ky = 111320, best = Infinity;
    rings(g).forEach(function (p) { p.forEach(function (r) {
      for (var i = 0; i < r.length; i++) {
        var a = r[i], b = r[(i + 1) % r.length];
        best = Math.min(best, segDist((a[0] - lon) * kx, (a[1] - lat) * ky, (b[0] - lon) * kx, (b[1] - lat) * ky));
      }
    }); });
    return best;
  }

  function matchStatic(rows, features) {
    var byId = {};
    features.forEach(function (f) { byId[f.properties.id] = f; });
    var out = rows.map(function (r, i) {
      var o = { row: i + 1, ref: r.ref, building_id: null, match_status: "unmatched", match_method: null, distance_m: null, note: null };
      var notes = [];
      if (r.building_id && byId[r.building_id]) { o.building_id = r.building_id; o.match_status = "matched"; o.match_method = "building_id"; }
      else {
        if (r.building_id) notes.push("building_id not found");
        var lat = parseFloat(r.lat), lon = parseFloat(r.lon);
        if (r.lat != null && r.lon != null && isFinite(lat) && isFinite(lon)) {
          var inside = null, best = null, bd = Infinity;
          features.forEach(function (f) {
            if (inside) return;
            if (f.geometry.type !== "Point" && contains(f.geometry, lat, lon)) { inside = f; return; }
            var d = distM(f.geometry, lat, lon);
            if (d < bd) { bd = d; best = f; }
          });
          if (inside) { o.building_id = inside.properties.id; o.match_status = "matched"; o.match_method = "point_in_polygon"; o.distance_m = 0; }
          else if (best && bd <= NEAREST_M) { o.building_id = best.properties.id; o.match_status = "matched"; o.match_method = "nearest_footprint"; o.distance_m = Math.round(bd * 10) / 10; }
          else notes.push("no footprint within " + NEAREST_M + " m");
        } else if (r.lat != null || r.lon != null) notes.push("lat/lon not valid numbers");
        if (!o.building_id && r.address) notes.push("address matching needs the live API");
        if (!r.building_id && !r.address && (r.lat == null || r.lon == null)) { o.match_status = "invalid"; notes.push("row has no building_id, lat/lon or address"); }
      }
      o.note = notes.join("; ") || null;
      if (o.building_id) {
        var p = byId[o.building_id].properties;
        o.coverage_status = p.status; o.provenance = p.prov === "NONE" ? null : p.prov; o.sessions_needed = p.sessions_needed || null;
        o.score = p.released ? { value: p.score, lo: p.score_lo, hi: p.score_hi } : null;
        o.f1 = p.released && p.f1 != null ? { value: p.f1, lo: p.f1_lo, hi: p.f1_hi } : null;
      }
      return o;
    });
    var scores = out.filter(function (o) { return o.score; }).map(function (o) { return o.score.value; }).sort(function (a, b) { return a - b; });
    var matched = out.filter(function (o) { return o.match_status === "matched"; }).length;
    var pct = function (q) { if (!scores.length) return null; var p = (scores.length - 1) * q, lo = Math.floor(p), hi = Math.ceil(p); return Math.round((scores[lo] + (scores[hi] - scores[lo]) * (p - lo)) * 10) / 10; };
    var bins = [0, 20, 40, 60, 80].map(function (lo, i) { return { lo: lo, hi: lo + 20, count: scores.filter(function (s) { return s >= lo && (s < lo + 20 || (i === 4 && s <= 100)); }).length }; });
    var methods = {};
    out.forEach(function (o) { if (o.match_method) methods[o.match_method] = (methods[o.match_method] || 0) + 1; });
    return { rows: out, summary: { rows: out.length, matched: matched, scored: scores.length,
      unmatched: out.filter(function (o) { return o.match_status === "unmatched"; }).length,
      invalid: out.filter(function (o) { return o.match_status === "invalid"; }).length,
      coverage_pct: matched ? Math.round(1000 * scores.length / matched) / 10 : 0,
      match_methods: methods, score_distribution: { bins: bins, median: pct(0.5), p10: pct(0.1), p90: pct(0.9), n: scores.length } } };
  }

  function render(res, el, ctx) {
    var s = res.summary;
    var maxBin = Math.max.apply(null, s.score_distribution.bins.map(function (b) { return b.count; }).concat([1]));
    var h = '<div class="summary-grid">' +
      stat(s.rows, "rows") + stat(s.matched, "matched") + stat(s.scored, "scored (released)") + stat(fmt(s.coverage_pct, 1) + "%", "of matched have a score") + "</div>";
    h += '<div class="card" style="margin-bottom:12px"><div class="small" style="font-weight:600;margin-bottom:6px">Score distribution of released buildings</div>' +
      '<div style="display:flex;gap:6px;align-items:flex-end;height:70px">' +
      s.score_distribution.bins.map(function (b) {
        return '<div style="flex:1;text-align:center" title="' + b.count + ' buildings"><div style="height:' + Math.round(50 * b.count / maxBin) + 'px;border-radius:6px 6px 2px 2px;background:' + C.rampColor(C.SCORE_STOPS, b.lo + 10) + '"></div><div class="tiny muted">' + b.lo + "-" + b.hi + "</div></div>";
      }).join("") + "</div>" +
      '<div class="tiny muted" style="margin-top:6px">Median ' + fmt(s.score_distribution.median) + " (p10 " + fmt(s.score_distribution.p10) + ", p90 " + fmt(s.score_distribution.p90) +
      "). Each building's own band is in the table. Methods: " + esc(Object.keys(s.match_methods || {}).map(function (k) { return k + " " + s.match_methods[k]; }).join(", ") || "none") + "</div></div>";
    h += '<div style="display:flex;justify-content:flex-end;margin-bottom:8px"><button class="btn" id="pDownload">Download results CSV</button></div>';
    h += '<div class="tbl-wrap"><table class="pf"><thead><tr><th>Row</th><th>Ref</th><th>Match</th><th>Building</th><th>Method</th><th>Distance</th><th>Coverage</th><th>Score (5-95%)</th><th>f1 (Hz)</th><th>Provenance</th><th>Note</th></tr></thead><tbody>';
    res.rows.slice(0, 500).forEach(function (o) {
      h += "<tr><td>" + o.row + "</td><td>" + esc(o.ref) + "</td><td>" + esc(o.match_status) + "</td><td>" +
        (o.building_id ? '<button class="link" data-bid="' + esc(o.building_id) + '">' + esc(o.building_id) + "</button>" : "–") + "</td><td>" +
        esc(o.match_method || "–") + "</td><td>" + (o.distance_m != null ? fmt(o.distance_m, 1) + " m" : "–") + "</td><td>" + esc(o.coverage_status || "–") +
        "</td><td>" + (o.score ? fmt(o.score.value) + " (" + fmt(o.score.lo) + "–" + fmt(o.score.hi) + ")" : "–") + "</td><td>" +
        (o.f1 ? fmt(o.f1.value, 2) + " (" + fmt(o.f1.lo, 2) + "–" + fmt(o.f1.hi, 2) + ")" : "–") + "</td><td>" + esc(o.provenance || "–") + '</td><td class="muted">' + esc(o.note || "") + "</td></tr>";
    });
    h += "</tbody></table></div>";
    if (res.rows.length > 500) h += '<p class="tiny muted">Showing the first 500 rows; the download has all of them.</p>';
    el.innerHTML = h;
    el.querySelectorAll("button[data-bid]").forEach(function (b) {
      b.addEventListener("click", function () { ctx.select(b.getAttribute("data-bid")); });
    });
    el.querySelector("#pDownload").addEventListener("click", function () { download(res.rows); });
  }
  function stat(v, label) { return '<div class="stat"><b>' + esc(v) + "</b><span>" + esc(label) + "</span></div>"; }

  function download(rows) {
    var cols = ["row", "ref", "match_status", "building_id", "match_method", "distance_m", "coverage_status", "score", "score_lo", "score_hi", "f1_hz", "f1_lo_hz", "f1_hi_hz", "provenance", "note"];
    var q = function (v) { v = v == null ? "" : String(v); return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; };
    var lines = [cols.join(",")].concat(rows.map(function (o) {
      return [o.row, o.ref, o.match_status, o.building_id, o.match_method, o.distance_m, o.coverage_status,
        o.score && o.score.value, o.score && o.score.lo, o.score && o.score.hi, o.f1 && o.f1.value, o.f1 && o.f1.lo, o.f1 && o.f1.hi, o.provenance, o.note].map(q).join(",");
    }));
    var a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([lines.join("\n") + "\n"], { type: "text/csv" }));
    a.download = "quakescore_portfolio_matches.csv";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 1000);
  }

  function sampleCSV(features) {
    var f = features.filter(function (x) { return x.geometry.type !== "Point"; });
    var lines = ["ref,building_id,lat,lon,address"];
    for (var i = 0; i < Math.min(f.length, 12); i++) {
      var g = f[(i * 53) % f.length], r = g.geometry.type === "Polygon" ? g.geometry.coordinates[0] : g.geometry.coordinates[0][0];
      var cx = 0, cy = 0; r.slice(0, -1).forEach(function (p) { cx += p[0]; cy += p[1]; }); cx /= r.length - 1; cy /= r.length - 1;
      if (i % 3 === 0) lines.push("asset-" + (i + 1) + "," + g.properties.id + ",,,");
      else if (i % 3 === 1) lines.push("asset-" + (i + 1) + ",," + cy.toFixed(6) + "," + cx.toFixed(6) + ",");
      else lines.push("asset-" + (i + 1) + ",,,," + JSON.stringify(g.properties.address || "1 Unknown Street"));
    }
    lines.push("asset-off-map,,37.70000,-122.30000,");
    return lines.join("\n") + "\n";
  }

  function init(ctx) {
    var dlg = document.getElementById("portfolioDlg"), out = document.getElementById("pOut"), drop = document.getElementById("pDrop");
    document.getElementById("pMode").innerHTML = ctx.live() && ctx.key()
      ? "<strong>Live API mode.</strong> The CSV is sent to " + esc(ctx.api) + "/v1/portfolio and matched on building_id, lat/lon and address."
      : "<strong>Static mode.</strong> Matching runs in your browser on <code>building_id</code> and <code>lat</code>/<code>lon</code> only (point in footprint, else nearest footprint within 30 m). Address matching needs the live API" +
        (ctx.live() ? " and an API key." : ".");
    async function handle(text) {
      out.innerHTML = '<div class="skeleton"></div><div class="skeleton" style="width:70%"></div>';
      try {
        var res;
        if (ctx.live() && ctx.key()) {
          var r = await fetch(ctx.api + "/v1/portfolio", { method: "POST", headers: { "Content-Type": "text/csv", "X-API-Key": ctx.key() }, body: text });
          var j = await r.json();
          if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail));
          res = j;
        } else {
          res = matchStatic(rowsFromCSV(text), ctx.features());
        }
        render(res, out, ctx);
      } catch (e) {
        out.innerHTML = '<p class="callout flag">Could not process this file: ' + esc(e.message) + "</p>";
      }
    }
    document.getElementById("pFile").addEventListener("change", function (e) {
      var f = e.target.files[0]; if (!f) return;
      f.text().then(handle); e.target.value = "";
    });
    document.getElementById("pSample").addEventListener("click", function () { handle(sampleCSV(ctx.features())); });
    ["dragenter", "dragover"].forEach(function (t) { drop.addEventListener(t, function (e) { e.preventDefault(); drop.classList.add("over"); }); });
    ["dragleave", "drop"].forEach(function (t) { drop.addEventListener(t, function (e) { e.preventDefault(); drop.classList.remove("over"); }); });
    drop.addEventListener("drop", function (e) { var f = e.dataTransfer.files[0]; if (f) f.text().then(handle); });
    return dlg;
  }

  window.QSPortfolio = { init: init, matchStatic: matchStatic, rowsFromCSV: rowsFromCSV, parseCSV: parseCSV };
})();
