/* QuakeScore demo dashboard: map, layers, provenance, building detail. */
(function () {
  "use strict";
  var C = window.QSCharts, esc = C.esc, fmt = C.fmt;

  // ------------------------------------------------------------------ configuration
  var params = new URLSearchParams(location.search);
  var API = (params.get("api") || "").replace(/\/+$/, "");
  if (API && !/^https?:\/\//i.test(API)) API = "";
  function store(k, v) {
    try { if (v === undefined) return sessionStorage.getItem(k); if (v) sessionStorage.setItem(k, v); else sessionStorage.removeItem(k); } catch (e) { return null; }
    return null;
  }
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var dark = window.matchMedia("(prefers-color-scheme: dark)");

  var state = { fc: null, meta: null, layer: "score", provs: null, selected: null, byId: {} };

  // ------------------------------------------------------------------ colour scales (colour-blind safe)
  var LAYERS = {
    score: {
      prop: "score", title: "QuakeScore", unit: "Score 0-100, unitless. 100 = least vulnerable.",
      stops: C.SCORE_STOPS, ends: ["0 most vulnerable", "50", "100 least vulnerable"],
      note: "Colour shows the central estimate; open a building to see its 5-95% band."
    },
    stiffness: {
      prop: "k_ratio", title: "Stiffness anomaly", unit: "k_ratio = (T_expected / T_measured)^2, unitless.",
      stops: [[0.5, "#b35806"], [0.75, "#fdb863"], [1.0, "#f7f7f7"], [1.25, "#b2abd2"], [1.5, "#542788"]],
      ends: ["0.5 softer", "1.0 as expected", "1.5 stiffer"], flag: "k_flag", flagLabel: "Flagged: softer under every plausible class"
    },
    drift: {
      prop: "drift_pct", title: "Frequency drift", unit: "Change of the fundamental frequency, % per year.",
      stops: [[-5, "#b35806"], [-2, "#fdb863"], [0, "#f7f7f7"], [2, "#b2abd2"], [5, "#542788"]],
      ends: ["-5 falling (softening)", "0", "+5 rising"], flag: "drift_alert", flagLabel: "Drift alert (sustained shift)"
    },
    coverage: { title: "Coverage status", unit: "Results are released at 3 contributors and 5 sessions." }
  };
  var COV = { scored: "#0072b2", needs_data: "#e69f00" };
  var NEVER = ["==", ["get", "id"], "__none__"];

  function fillColor(layer) {
    var L = LAYERS[layer];
    if (layer === "coverage") return ["match", ["get", "status"], "scored", COV.scored, "needs_data", COV.needs_data, "#999999"];
    var e = ["interpolate", ["linear"], ["get", L.prop]];
    L.stops.forEach(function (s) { e.push(s[0], s[1]); });
    return e;
  }
  function valueFilter(layer) {
    return layer === "coverage" ? ["==", ["get", "status"], "scored"] : ["has", LAYERS[layer].prop];
  }
  function gradientCSS(stops) {
    var a = stops[0][0], b = stops[stops.length - 1][0];
    return "linear-gradient(90deg," + stops.map(function (s) { return s[1] + " " + (100 * (s[0] - a) / (b - a)).toFixed(0) + "%"; }).join(",") + ")";
  }

  // ------------------------------------------------------------------ data access
  function key() { return store("qs_key"); }
  async function getJSON(url, withKey) {
    var h = {};
    if (withKey && key()) h["X-API-Key"] = key();
    var r = await fetch(url, { headers: h });
    if (!r.ok) throw new Error(url + " returned " + r.status);
    return r.json();
  }
  async function loadData() {
    if (!API) {
      var m = await getJSON("data/meta.json"), fc = await getJSON("data/buildings.geojson");
      return { meta: { provenance: m.provenance, generated: m.generated, k: m.k_threshold, synthetic: m.footprints_synthetic, source: "static files" }, fc: fc };
    }
    var meta = await getJSON(API + "/v1/meta");
    var fc2;
    if (key()) {
      fc2 = await getJSON(API + "/v1/buildings?limit=20000", true);
    } else {
      fc2 = await getJSON(API + "/v1/coverage");
      fc2.features.forEach(function (f) {
        var p = f.properties; p.prov = p.provenance || "NONE"; p.released = false; delete p.provenance;
      });
    }
    return { meta: { provenance: meta.result_provenance, k: meta.k_threshold, synthetic: meta.footprints_synthetic,
      source: "live API " + API + (key() ? "" : " (no API key: coverage only)") }, fc: fc2 };
  }

  // ------------------------------------------------------------------ provenance banner
  function isSim(p) { return p === "SIM" || p === "FIXTURE"; }
  function renderBanner(meta) {
    var el = document.getElementById("provBanner");
    var provs = meta.provenance || {};
    var names = Object.keys(provs).filter(function (k) { return provs[k] > 0; });
    var sim = names.filter(isSim), real = names.indexOf("REAL") >= 0;
    var label, sub = "";
    if (sim.length) {
      label = "Simulated data";
      sub = sim.indexOf("FIXTURE") >= 0 ? "FIXTURE placeholder records, not measurements" : "SIM: simulator output, not measurements";
      if (real) sub = "mixed: " + names.map(function (n) { return n + " " + provs[n]; }).join(", ");
      el.className = "prov-banner";
    } else if (real) {
      label = "Measured data (REAL)"; el.className = "prov-banner real";
    } else { label = "No results loaded"; el.className = "prov-banner"; }
    if (meta.synthetic) sub = (sub ? sub + "; " : "") + "synthetic footprints";
    el.innerHTML = '<span class="dot" aria-hidden="true"></span><span>' + esc(label) + (sub ? " <small>" + esc(sub) + "</small>" : "") + "</span>";
    el.title = sub;
  }

  // ------------------------------------------------------------------ map
  var map;
  function rasterPaint() {
    return dark.matches ? { "raster-saturation": -0.8, "raster-brightness-max": 0.42, "raster-brightness-min": 0.02, "raster-contrast": 0.1 }
      : { "raster-saturation": -0.65, "raster-brightness-min": 0.08 };
  }
  function ink() { return dark.matches ? "#f5f5f7" : "#1d1d1f"; }

  function hatchImage(color) {
    var n = 10, data = new Uint8Array(n * n * 4);
    var c = [parseInt(color.substr(1, 2), 16), parseInt(color.substr(3, 2), 16), parseInt(color.substr(5, 2), 16)];
    for (var y = 0; y < n; y++) for (var x = 0; x < n; x++) {
      var on = ((x + y) % n) < 3, i = (y * n + x) * 4;
      data[i] = c[0]; data[i + 1] = c[1]; data[i + 2] = c[2]; data[i + 3] = on ? 235 : 40;
    }
    return { width: n, height: n, data: data };
  }

  function initMap(fc, bbox) {
    map = new maplibregl.Map({
      container: "map",
      style: {
        version: 8,
        sources: { osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256, maxzoom: 19,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' } },
        layers: [{ id: "osm", type: "raster", source: "osm", paint: rasterPaint() }]
      },
      bounds: bbox, fitBoundsOptions: { padding: { top: 110, bottom: 140, left: 40, right: 40 } },
      maxZoom: 19, attributionControl: { compact: false }, preserveDrawingBuffer: params.has("debug")
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.on("error", function (e) { if (window.QSDebug.log) window.QSDebug.log("map: " + (e.error && e.error.message)); });
    map.on("idle", function () {
      if (window.QSDebug.log && map.getLayer("b-fill")) window.QSDebug.log("idle: rendered " + map.queryRenderedFeatures({ layers: ["b-fill", "b-hatch", "b-nodata"] }).length + " building features, zoom " + map.getZoom().toFixed(1));
    });
    // style.load: add data layers as soon as the style is ready, without waiting for every OSM tile
    map.once("style.load", function () {
      map.addImage("hatch-g", hatchImage("#8a8a94"));
      map.addImage("hatch-o", hatchImage("#e69f00"));
      map.addSource("b", { type: "geojson", data: fc, promoteId: "id" });
      map.addLayer({ id: "b-nodata", type: "fill", source: "b", filter: ["==", ["get", "status"], "no_data"],
        paint: { "fill-color": dark.matches ? "#2a2a2e" : "#ffffff", "fill-opacity": 0.55 } });
      map.addLayer({ id: "b-hatch", type: "fill", source: "b", paint: { "fill-pattern": "hatch-g", "fill-opacity": 0.95 } });
      map.addLayer({ id: "b-fill", type: "fill", source: "b", paint: { "fill-color": "#999", "fill-opacity": 0.88 } });
      map.addLayer({ id: "b-line-real", type: "line", source: "b", filter: ["==", ["get", "prov"], "REAL"],
        paint: { "line-color": ink(), "line-width": 1.1, "line-opacity": 0.75 } });
      map.addLayer({ id: "b-line-sim", type: "line", source: "b", filter: ["!=", ["get", "prov"], "REAL"],
        paint: { "line-color": ink(), "line-width": 1.0, "line-opacity": 0.6, "line-dasharray": [2, 1.5] } });
      map.addLayer({ id: "b-flag", type: "line", source: "b", filter: NEVER,
        paint: { "line-color": ink(), "line-width": 3.2 } });
      map.addLayer({ id: "b-sel", type: "line", source: "b", filter: ["==", ["get", "id"], ""],
        paint: { "line-color": dark.matches ? "#69a8ff" : "#0067db", "line-width": 3.5 } });
      ["b-fill", "b-hatch", "b-nodata"].forEach(function (id) {
        map.on("click", id, function (e) { if (e.features && e.features[0]) select(e.features[0].properties.id, false); });
        map.on("mouseenter", id, function () { map.getCanvas().style.cursor = "pointer"; });
        map.on("mouseleave", id, function () { map.getCanvas().style.cursor = ""; });
      });
      applyLayer();
      if (state.pendingSelect) { select(state.pendingSelect, true); state.pendingSelect = null; }
    });
    dark.addEventListener("change", function () {
      if (!map.isStyleLoaded()) return;
      var p = rasterPaint();
      ["raster-saturation", "raster-brightness-max", "raster-brightness-min", "raster-contrast"].forEach(function (k) {
        map.setPaintProperty("osm", k, p[k] == null ? (k === "raster-brightness-max" ? 1 : 0) : p[k]);
      });
      ["b-line-real", "b-line-sim", "b-flag"].forEach(function (id) { map.setPaintProperty(id, "line-color", ink()); });
      map.setPaintProperty("b-nodata", "fill-color", dark.matches ? "#2a2a2e" : "#ffffff");
      map.setPaintProperty("b-sel", "line-color", dark.matches ? "#69a8ff" : "#0067db");
    });
  }

  function provFilter() {
    return ["in", ["get", "prov"], ["literal", state.provs]];
  }
  function applyLayer() {
    if (!map || !map.getLayer("b-fill")) return;
    var L = state.layer, vf = valueFilter(L), pf = provFilter();
    map.setPaintProperty("b-fill", "fill-color", fillColor(L));
    map.setFilter("b-fill", ["all", pf, vf]);
    map.setFilter("b-hatch", ["all", pf, ["!", vf], ["!=", ["get", "status"], "no_data"]]);
    map.setPaintProperty("b-hatch", "fill-pattern", L === "coverage" ? "hatch-o" : "hatch-g");
    map.setFilter("b-nodata", ["all", pf, ["==", ["get", "status"], "no_data"]]);
    map.setFilter("b-line-real", ["all", pf, ["==", ["get", "prov"], "REAL"]]);
    map.setFilter("b-line-sim", ["all", pf, ["!=", ["get", "prov"], "REAL"]]);
    var flag = LAYERS[L].flag;
    map.setFilter("b-flag", flag ? ["all", pf, ["==", ["get", flag], true]] : NEVER);
    renderLegend();
  }

  // ------------------------------------------------------------------ legend
  function renderLegend() {
    var L = LAYERS[state.layer], el = document.getElementById("legend");
    var counts = { scored: 0, needs_data: 0, no_data: 0 };
    state.fc.features.forEach(function (f) { if (state.provs.indexOf(f.properties.prov) >= 0) counts[f.properties.status]++; });
    var h = "<h2>" + esc(L.title) + "</h2><div class='tiny muted'>" + esc(L.unit) + "</div>";
    if (L.stops) {
      h += '<div class="ramp" style="background:' + gradientCSS(L.stops) + '"></div><div class="ends">' + L.ends.map(function (e) { return "<span>" + esc(e) + "</span>"; }).join("") + "</div>";
      if (L.note) h += '<div class="tiny muted" style="margin-top:4px">' + esc(L.note) + "</div>";
    }
    h += "<details" + (window.innerWidth > 760 ? " open" : "") + "><summary>Key</summary><div class='keys'>";
    if (state.layer === "coverage") {
      h += key_("solid", "Scored and released (" + counts.scored + ")", COV.scored);
      h += key_("hatch-o", "Collecting data, not yet released (" + counts.needs_data + ")");
    } else {
      h += key_("hatch", state.layer === "score" ? "Collecting data: no score yet (" + counts.needs_data + ")" : "No value: not yet released or not available");
    }
    h += key_("empty", "No measurements yet (" + counts.no_data + ")");
    if (L.flag) h += key_("flag", L.flagLabel);
    h += key_("solid-o", "Outline solid: REAL data");
    h += key_("dash", "Outline dashed: SIM or FIXTURE data");
    h += "</div></details>";
    el.innerHTML = h;
  }
  function key_(kind, label, color) {
    var cls = kind === "solid" ? "swatch" : kind === "solid-o" ? "swatch solid" : "swatch " + kind;
    return '<div class="key"><span class="' + cls + '"' + (color ? ' style="background:' + color + '"' : "") + '></span><span>' + esc(label) + "</span></div>";
  }

  // ------------------------------------------------------------------ provenance filter
  function renderProvFilter() {
    var present = {};
    state.fc.features.forEach(function (f) { present[f.properties.prov] = (present[f.properties.prov] || 0) + 1; });
    var labels = { REAL: "REAL (measured)", SIM: "SIM (simulator)", FIXTURE: "FIXTURE (placeholder)", NONE: "No result record" };
    state.provs = Object.keys(present);
    var fs = document.getElementById("provFilter");
    fs.innerHTML = "<legend>Data provenance</legend>" + ["REAL", "SIM", "FIXTURE", "NONE"].map(function (p) {
      var n = present[p] || 0;
      return '<label class="check"><input type="checkbox" value="' + p + '"' + (n ? " checked" : " disabled") + "> " + esc(labels[p]) + ' <span class="muted num">' + n + "</span></label>";
    }).join("");
    fs.addEventListener("change", function () {
      state.provs = Array.prototype.map.call(fs.querySelectorAll("input:checked"), function (i) { return i.value; });
      applyLayer();
    });
  }

  // ------------------------------------------------------------------ building detail
  var sheet = document.getElementById("detail"), dBody = document.getElementById("dBody");
  var lastFocus = null;

  function provNote(prov) {
    if (prov === "FIXTURE") return '<div class="sim-note" role="note"><div><strong>Simulated data</strong>FIXTURE: a fabricated placeholder record used to build this demo. Not a measurement of this building.</div></div>';
    if (prov === "SIM") return '<div class="sim-note" role="note"><div><strong>Simulated data</strong>SIM: produced by the QuakeScore simulator. Not a measurement of this building.</div></div>';
    if (prov === "REAL") return '<div class="real-note">REAL: measured with phones in this building.</div>';
    return '<div class="callout">No result record for this building yet.</div>';
  }

  function setProvPill(prov) {   // always visible in the sheet header, even when scrolled
    var el = document.getElementById("dProv");
    if (isSim(prov)) el.innerHTML = '<span class="prov-pill">Simulated data · ' + esc(prov) + "</span>";
    else if (prov === "REAL") el.innerHTML = '<span class="prov-pill real">REAL · measured</span>';
    else el.innerHTML = '<span class="prov-pill none">No result record</span>';
  }

  function stiffnessReading(st, cls) {
    if (!st || st.k_ratio == null) return "No stiffness estimate.";
    var k = st.k_ratio, pct = Math.round(Math.abs(1 - k) * 100);
    var cname = cls ? " for its most likely class (" + cls + ")" : " for its class";
    if (pct < 5) return "About as stiff as expected" + cname + ".";
    return pct + "% " + (k < 1 ? "softer" : "stiffer") + " than expected" + cname + ".";
  }

  function coverageBlock(c) {
    var h = '<div class="stats">' +
      '<div class="stat"><b>' + c.sessions + "</b><span>sessions</span></div>" +
      '<div class="stat"><b>' + c.contributors + "</b><span>contributors</span></div>" +
      '<div class="stat"><b>' + c.floors + "</b><span>floors covered</span></div></div>";
    var k = c.k_threshold || { contributors: 3, sessions: 5 };
    if (c.status === "scored") h += '<p class="small muted">Meets the release threshold (' + k.contributors + " contributors, " + k.sessions + " sessions). More sessions on more floors narrow the bands.</p>";
    else {
      var need = [];
      if (c.sessions_needed) need.push(c.sessions_needed + " more session" + (c.sessions_needed > 1 ? "s" : ""));
      if (c.contributors_needed) need.push(c.contributors_needed + " more contributor" + (c.contributors_needed > 1 ? "s" : ""));
      h += '<div class="callout" style="margin-top:8px"><strong>' + (c.status === "no_data" ? "No measurements yet." : "Collecting data.") + "</strong> " +
        "Results are released only after " + k.contributors + " different contributors and " + k.sessions + " sessions, so no household can be identified. " +
        (need.length ? "Still needed: " + esc(need.join(" and ")) + "." : "The threshold is met, but the batch has not yet identified a structural mode.") + "</div>";
    }
    return h;
  }

  function modesTable(modes) {
    if (!modes || !modes.length) return '<p class="muted small">No modes identified.</p>';
    var h = '<table class="modes"><thead><tr><th>Peak</th><th>f (Hz)</th><th>Damping</th><th>z</th></tr></thead><tbody>';
    modes.forEach(function (m, i) {
      var ok = m.label === "structural";
      h += '<tr class="' + (ok ? "" : "rejected") + '"><td>' + (ok ? '<span class="tag ok">structural</span>' : '<span class="tag">' + esc(String(m.label).replace("rejected:", "rejected: ")) + "</span>") + "</td>" +
        "<td>" + fmt(m.f, 3) + '<span class="ci">' + fmt(m.f_lo, 3) + "–" + fmt(m.f_hi, 3) + "</span></td>" +
        "<td>" + fmt(m.zeta * 100, 2) + '%<span class="ci">' + fmt(m.zeta_lo * 100, 2) + "–" + fmt(m.zeta_hi * 100, 2) + "%</span></td>" +
        "<td>" + fmt(m.z, 1) + "</td></tr>";
    });
    return h + '</tbody></table><p class="tiny muted">Ranges are 90% intervals from resampling sessions. z is the detection score of the peak; rejected peaks failed an artefact test (tone, width, fleet, persistence, ...).</p>';
  }

  function section(title, body) { return '<section class="section"><h3>' + esc(title) + "</h3>" + body + "</section>"; }

  function renderDetail(v) {
    var a = v.attrs || {}, c = v.coverage;
    document.getElementById("dTitle").textContent = a.name || a.address || "Unnamed building";
    document.getElementById("dSub").textContent = [a.name && a.address ? a.address : null, v.building_id,
      a.storeys ? a.storeys + " storeys" : null, a.year ? "built " + a.year : null].filter(Boolean).join(" · ");
    setProvPill(v.provenance);
    var h = '<section class="section">' + provNote(v.provenance) + "</section>";
    if (v.released) {
      var s = v.score;
      h += section("QuakeScore", '<div class="score-big"><span class="v num">' + fmt(s.value, 0) + '</span><span class="band num">band ' + fmt(s.lo, 0) + "–" + fmt(s.hi, 0) + " (5-95%)</span></div>" +
        C.scoreBands(s) +
        '<p class="tiny muted" style="margin:4px 0 0">0 = most vulnerable, 100 = least vulnerable. "Prior only" uses public attributes alone; the measured score adds this building\'s vibration data' +
        (s.prior_lo != null ? " and narrows the band from " + fmt(s.prior_hi - s.prior_lo, 0) + " to " + fmt(s.hi - s.lo, 0) + " points" : "") + ".</p>");
      var st = v.stiffness;
      h += section("Stiffness", '<div class="callout' + (st && st.flag ? " flag" : "") + '"><strong>' + esc(stiffnessReading(st, v.class_map)) + "</strong>" +
        (st ? '<div class="small muted num">k_ratio ' + fmt(st.k_ratio, 2) + " · z " + fmt(st.z, 1) + " against class scatter · " +
          (st.flag ? "flagged: anomalous under every plausible class" : "not flagged") + "</div>" : "") + "</div>");
      h += section("Structural class", '<div class="small" style="margin-bottom:4px">Most likely <strong>' + esc(v.class_map || "–") + "</strong> · GEM <span class='num'>" + esc(v.gem_taxonomy || "–") + "</span></div>" + C.classBars(v.class_probs));
      h += section("Modes", '<p class="small" style="margin-top:0">Fundamental frequency <strong class="num">' + fmt(v.f1, 3) + " Hz</strong> <span class='muted num'>(" + fmt(v.f1_lo, 3) + "–" + fmt(v.f1_hi, 3) + ")</span>, damping <strong class='num'>" +
        fmt(v.zeta1 * 100, 2) + "%</strong> <span class='muted num'>(" + fmt(v.zeta1_lo * 100, 2) + "–" + fmt(v.zeta1_hi * 100, 2) + "%)</span></p>" + modesTable(v.modes));
      if (v.damage) h += section("Damage probabilities", '<p class="tiny muted" style="margin-top:0">Probability of each damage state for three standard shaking scenarios (peak ground acceleration).</p>' + C.damageBars(v.damage));
      if (v.drift) {
        var d = v.drift;
        h += section("Frequency drift", (d.alert ? '<div class="callout flag"><strong>Drift alert.</strong> A sustained shift in frequency was detected' + (d.step_pct != null ? " (step " + fmt(d.step_pct, 1) + "%)" : "") + ". This can have benign causes; it is a prompt for inspection, not a finding.</div>" : "") +
          '<p class="small" style="margin:6px 0">Trend <strong class="num">' + (d.pct_per_year == null ? "–" : (d.pct_per_year > 0 ? "+" : "") + fmt(d.pct_per_year, 2) + "% per year") + "</strong> <span class='muted'>(after temperature and amplitude correction)</span></p>" + C.driftChart(d));
      }
      if (v.spectrum) h += section("Stacked spectrum", '<p class="tiny muted" style="margin-top:0">Horizontal power of all sessions combined, divided by the fitted noise baseline.</p>' + C.spectrumChart(v.spectrum, v.modes));
      h += section("Coverage", coverageBlock(c));
    } else {
      h += section("Coverage", coverageBlock(c));
      h += section("How to help", '<p class="small" style="margin-top:0">Residents and workers can contribute by leaving a phone with the QuakeScore app flat on a table overnight while it charges. Only spectral summaries and the building id are uploaded.</p>');
    }
    h += '<p class="caveat">Statistical screening result, not a structural engineering assessment. Only a licensed structural engineer who inspects the building can assess its safety. ' +
      (v.updated ? "Updated " + esc(v.updated) + ". " : "") + "Footprint &copy; OpenStreetMap contributors.</p>";
    dBody.innerHTML = h;
  }

  function renderCard(card) {
    document.getElementById("dTitle").textContent = card.name || card.address || "Building";
    document.getElementById("dSub").textContent = card.building_id;
    setProvPill(card.provenance);
    var h = '<section class="section">' + provNote(card.provenance) + "</section>";
    if (card.score_band) {
      var s = card.score_band;
      h += section("QuakeScore band", '<div class="score-big"><span class="v num">' + fmt(s.value, 0) + '</span><span class="band num">band ' + fmt(s.lo, 0) + "–" + fmt(s.hi, 0) + " (5-95%)</span></div>" + C.scoreBands({ value: s.value, lo: s.lo, hi: s.hi }) +
        '<p class="tiny muted">Full parameters need a buyer API key.</p>');
    }
    h += section("Coverage", '<div class="stats"><div class="stat"><b>' + card.sessions + '</b><span>sessions</span></div><div class="stat"><b>' + card.contributors + "</b><span>contributors</span></div></div>" +
      (card.message ? '<p class="callout">' + esc(card.message) + "</p>" : ""));
    h += '<p class="caveat">' + esc(card.caveat) + " " + esc(card.inspection_route && card.inspection_route.text) + "</p>";
    dBody.innerHTML = h;
  }

  var reqSeq = 0;
  async function select(id, fly) {
    var f = state.byId[id];
    if (!f) { toast("Building " + id + " is not on this map."); return; }
    state.selected = id;
    if (map && map.getLayer("b-sel")) map.setFilter("b-sel", ["==", ["get", "id"], id]);
    if (location.hash !== "#b=" + encodeURIComponent(id)) history.replaceState(null, "", "#b=" + encodeURIComponent(id));
    if (sheet.hasAttribute("hidden")) lastFocus = document.activeElement;
    sheet.removeAttribute("hidden");
    var p = f.properties;
    document.getElementById("dTitle").textContent = p.name || p.address || "Unnamed building";
    document.getElementById("dSub").textContent = id;
    setProvPill(p.prov);
    dBody.innerHTML = '<div class="skeleton"></div><div class="skeleton" style="width:60%"></div><div class="skeleton" style="width:80%"></div>';
    if (fly && map) {
      var c = centroidOf(f.geometry);
      map.easeTo({ center: c, zoom: Math.max(map.getZoom(), 17), duration: reduceMotion ? 0 : 600 });
    }
    var my = ++reqSeq;
    try {
      var v;
      if (!API) v = await getJSON("data/b/" + encodeURIComponent(p.file));
      else if (key()) v = await getJSON(API + "/v1/buildings/" + id, true);
      else { var card = await getJSON(API + "/v1/buildings/" + id + "/public"); if (my === reqSeq) renderCard(card); return; }
      if (my === reqSeq) renderDetail(v);
    } catch (e) {
      if (my === reqSeq) dBody.innerHTML = '<p class="callout flag">Could not load this building: ' + esc(e.message) + "</p>";
    }
    sheet.focus({ preventScroll: true });
  }
  function closeDetail() {
    sheet.setAttribute("hidden", "");
    state.selected = null;
    if (map && map.getLayer("b-sel")) map.setFilter("b-sel", ["==", ["get", "id"], ""]);
    history.replaceState(null, "", location.pathname + location.search);
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  function centroidOf(g) {
    var r = g.type === "Polygon" ? g.coordinates[0] : g.type === "MultiPolygon" ? g.coordinates[0][0] : [g.coordinates];
    var x = 0, y = 0; r.forEach(function (p) { x += p[0]; y += p[1]; });
    return [x / r.length, y / r.length];
  }

  // ------------------------------------------------------------------ search
  function initSearch() {
    var q = document.getElementById("q"), list = document.getElementById("qList"), active = -1, items = [];
    function close() { list.hidden = true; q.setAttribute("aria-expanded", "false"); active = -1; }
    function show() {
      var t = q.value.trim().toLowerCase();
      if (t.length < 2) { close(); return; }
      items = state.fc.features.filter(function (f) {
        var p = f.properties; return [p.name, p.address, p.id].some(function (s) { return s && String(s).toLowerCase().indexOf(t) >= 0; });
      }).slice(0, 12);
      list.innerHTML = items.length ? items.map(function (f, i) {
        var p = f.properties;
        return '<li><button type="button" role="option" id="qo' + i + '" data-id="' + esc(p.id) + '"><div>' + esc(p.name || p.address || p.id) + '</div><div class="tiny muted">' + esc([p.address && p.name ? p.address : null, p.id, p.status.replace("_", " ")].filter(Boolean).join(" · ")) + "</div></button></li>";
      }).join("") : '<li class="small muted" style="padding:8px 10px">No matching building.</li>';
      list.hidden = false; q.setAttribute("aria-expanded", "true");
    }
    q.addEventListener("input", show);
    q.addEventListener("keydown", function (e) {
      var opts = list.querySelectorAll("button");
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault(); if (!opts.length) return;
        active = (active + (e.key === "ArrowDown" ? 1 : -1) + opts.length) % opts.length;
        opts.forEach(function (o, i) { o.setAttribute("aria-selected", i === active ? "true" : "false"); });
        q.setAttribute("aria-activedescendant", "qo" + active);
      } else if (e.key === "Enter" && opts.length) {
        e.preventDefault(); var b = opts[Math.max(active, 0)]; close(); select(b.getAttribute("data-id"), true);
      } else if (e.key === "Escape") close();
    });
    list.addEventListener("click", function (e) {
      var b = e.target.closest("button[data-id]"); if (!b) return; close(); select(b.getAttribute("data-id"), true);
    });
    document.addEventListener("click", function (e) { if (!e.target.closest(".search")) close(); });
  }

  // ------------------------------------------------------------------ misc UI
  function toast(msg) {
    var t = document.getElementById("toast"); t.textContent = msg; t.hidden = false;
    clearTimeout(toast._t); toast._t = setTimeout(function () { t.hidden = true; }, 3200);
  }
  function initChrome() {
    document.querySelectorAll('input[name="layer"]').forEach(function (r) {
      r.addEventListener("change", function () { state.layer = r.value; applyLayer(); });
    });
    var fb = document.getElementById("filterBtn"), fp = document.getElementById("filterPop");
    fb.addEventListener("click", function () { var open = fp.hidden; fp.hidden = !open; fb.setAttribute("aria-expanded", String(open)); });
    document.addEventListener("click", function (e) { if (!e.target.closest(".filters")) { fp.hidden = true; fb.setAttribute("aria-expanded", "false"); } });
    document.getElementById("dClose").addEventListener("click", closeDetail);
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !sheet.hasAttribute("hidden") && !document.querySelector("dialog[open]")) closeDetail();
    });
    var about = document.getElementById("aboutDlg");
    document.getElementById("aboutBtn").addEventListener("click", function () { about.showModal(); });
    document.getElementById("whatBtn").addEventListener("click", function () { about.showModal(); });
    document.querySelectorAll("dialog [data-close]").forEach(function (b) { b.addEventListener("click", function () { b.closest("dialog").close(); }); });
    document.querySelectorAll("dialog").forEach(function (d) {
      d.addEventListener("click", function (e) { if (e.target === d) d.close(); });
    });
    var ak = document.getElementById("apiKey");
    if (!API) document.getElementById("liveBox").querySelector("p").insertAdjacentHTML("beforeend", " This page is currently reading static files.");
    document.getElementById("apiKeySave").addEventListener("click", function () { store("qs_key", ak.value.trim() || null); location.reload(); });
    window.addEventListener("hashchange", function () {
      var m = location.hash.match(/^#b=(.+)$/); if (m) select(decodeURIComponent(m[1]), true);
    });
  }

  // ------------------------------------------------------------------ boot
  function trackTopbar() {   // the detail sheet sits below the floating top bar, whose height wraps
    var bar = document.querySelector(".topbar");
    var set = function () { document.documentElement.style.setProperty("--topbar-bottom", Math.round(bar.getBoundingClientRect().bottom) + "px"); };
    set();
    if (window.ResizeObserver) new ResizeObserver(set).observe(bar); else window.addEventListener("resize", set);
  }

  async function boot() {
    initChrome();
    trackTopbar();
    var data;
    try { data = await loadData(); }
    catch (e) {
      document.getElementById("provBanner").innerHTML = '<span class="dot"></span><span>Data failed to load</span>';
      document.getElementById("legend").innerHTML = '<p class="small">Could not load building data (' + esc(e.message) + "). Run <code>python -m quakescore.service.export_static dashboard/data</code> and serve the dashboard folder over HTTP.</p>";
      return;
    }
    state.fc = data.fc; state.meta = data.meta;
    state.fc.features.forEach(function (f) { state.byId[f.properties.id] = f; });
    renderBanner(data.meta);
    renderProvFilter();
    document.getElementById("aboutData").textContent = "Data source: " + data.meta.source + (data.meta.generated ? ", exported " + data.meta.generated : "") +
      ". " + state.fc.features.length + " buildings. Release threshold: " + (data.meta.k ? data.meta.k.contributors + " contributors and " + data.meta.k.sessions + " sessions." : "");
    var xs = [], ys = [];
    state.fc.features.forEach(function (f) { var c = centroidOf(f.geometry); xs.push(c[0]); ys.push(c[1]); });
    var bbox = xs.length ? [[Math.min.apply(null, xs), Math.min.apply(null, ys)], [Math.max.apply(null, xs), Math.max.apply(null, ys)]] : [[-122.405, 37.786], [-122.392, 37.796]];
    var m = location.hash.match(/^#b=(.+)$/); if (m) state.pendingSelect = decodeURIComponent(m[1]);
    renderLegend();
    initMap(state.fc, bbox);
    initSearch();
    var pdlg = window.QSPortfolio.init({ api: API, live: function () { return !!API; }, key: key, features: function () { return state.fc.features; },
      select: function (id) { pdlg.close(); select(id, true); } });
    document.getElementById("portfolioBtn").addEventListener("click", function () { pdlg.showModal(); });
  }
  window.QSDebug = { state: state, map: function () { return map; } };
  if (params.has("debug")) {   // ?debug=1 shows script errors on the page (used for headless checks)
    var dbg = document.createElement("pre");
    dbg.id = "debugLog";
    dbg.style.cssText = "position:fixed;z-index:99;left:8px;top:130px;max-width:60%;font-size:11px;background:#fff;color:#000;white-space:pre-wrap;margin:0";
    document.body.appendChild(dbg);
    var log = function (m) { dbg.textContent += m + "\n"; };
    window.addEventListener("error", function (e) { log("error: " + e.message); });
    window.addEventListener("unhandledrejection", function (e) { log("rejection: " + (e.reason && e.reason.message || e.reason)); });
    QSDebug.log = log;
    log("viewport " + innerWidth + "x" + innerHeight);
  }
  boot();
})();
