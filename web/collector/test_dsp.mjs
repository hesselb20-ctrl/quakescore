// Test runner for dsp.js against tests/vectors (written by experiments/export_device_vectors.py).
// Run from the repository root:  node web/collector/test_dsp.mjs
//
// Mirrors android/dsp-core StreamingVectorTest.kt and BuildingBlocksTest.kt, with the same tolerances:
// exact counts, indices, flags and session end; mean CSD and p4 to RTOL = 2e-5 relative on bins above
// the noise floor (per axis Gii > 1e-4 x median of Gii over the band), off-diagonal terms relative to
// sqrt(Gii * Gjj). Prints one line per check and exits non-zero on any failure.
import { readFileSync } from "node:fs";
import { gunzipSync } from "node:zlib";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import {
  AnchoredDecimator, Fft, GridResampler, NBINS, NFFT, SessionProcessor, fromBase64LE, levelRotation,
  toBase64LE,
} from "./dsp.js";
import { TAPS2, TAPS4 } from "./fir_taps.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const VEC = process.env.QS_VECTORS || join(HERE, "..", "..", "tests", "vectors");
const RTOL = 2e-5;

let failures = 0;
function report(ok, label, detail = "") {
  if (!ok) failures++;
  console.log(`${ok ? "PASS" : "FAIL"} ${label}${detail ? "  " + detail : ""}`);
}
function check(label, fn) {
  try {
    const detail = fn();
    report(true, label, detail || "");
  } catch (e) {
    report(false, label, e && e.message ? e.message : String(e));
  }
}
function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}
function assertEq(exp, got, what) {
  assert(Object.is(exp, got) || exp === got, `${what}: expected ${exp}, got ${got}`);
}
function assertClose(exp, got, tol, what) {
  assert(Math.abs(exp - got) <= tol, `${what}: expected ${exp}, got ${got} (tol ${tol})`);
}
function assertList(exp, got, what) {
  assert(exp.length === got.length, `${what}: length ${got.length}, expected ${exp.length}`);
  for (let i = 0; i < exp.length; i++) assert(exp[i] === got[i], `${what}[${i}]: expected ${exp[i]}, got ${got[i]}`);
}

const json = (name) => JSON.parse(readFileSync(join(VEC, name), "utf8"));

/** Parses a stream_*.csv.gz exactly as Vectors.kt feed() does. */
function loadStream(name, t0, lsb) {
  const text = gunzipSync(readFileSync(join(VEC, name))).toString("utf8");
  const lines = text.split("\n");
  const t = new Float64Array(lines.length), x = new Float64Array(lines.length);
  const y = new Float64Array(lines.length), z = new Float64Array(lines.length);
  let n = 0, off = 0;
  for (const line of lines) {
    if (line.trim() === "") continue;
    const f = line.split(",");
    off += Number(f[0]);                    // integer ns, exact as a Number below 2^53
    if (!Number.isSafeInteger(off)) throw new Error("offset beyond 2^53");
    t[n] = t0 + off * 1e-9;
    x[n] = Number(f[1]) * lsb;
    y[n] = Number(f[2]) * lsb;
    z[n] = Number(f[3]) * lsb;
    n++;
  }
  return { n, t, x, y, z };
}

function feed(p, s, from = 0, to = s.n) {
  for (let i = from; i < to; i++) p.push(s.t[i], s.x[i], s.y[i], s.z[i]);
}

function medianOf(arr) {
  const s = Float64Array.from(arr).sort();
  const h = Math.floor(s.length / 2);
  return s.length % 2 ? s[h] : (s[h - 1] + s[h]) / 2;
}

/** StreamingVectorTest.compare: returns { checked, worst }. */
function compareBand(label, ec, ac, ep, ap) {
  assertEq(NBINS * 9, ec.length, `${label} expected csd length`);
  assertEq(NBINS * 3, ep.length, `${label} expected p4 length`);
  assertEq(NBINS * 9, ac.length, `${label} csd length`);
  assertEq(NBINS * 3, ap.length, `${label} p4 length`);
  const floor = [0, 1, 2].map((i) => {
    const col = new Float64Array(NBINS);
    for (let f = 0; f < NBINS; f++) col[f] = ec[9 * f + i];
    return 1e-4 * medianOf(col);
  });
  if (floor.every((v) => v === 0)) {
    assert(ac.every((v) => v === 0) && ap.every((v) => v === 0), `${label} expected all zeros`);
    return { checked: 0, worst: 0, zeros: true };
  }
  let worst = 0, checked = 0;
  const rel = (a, e, scale, what) => {
    const err = Math.abs(a - e) / scale;
    assert(err <= RTOL, `${label} ${what}: got ${a} expected ${e} (relative ${err})`);
    return err;
  };
  const pairs = [[3, 0, 1], [5, 0, 2], [7, 1, 2]];
  for (let f = 0; f < NBINS; f++) {
    const g = [ec[9 * f], ec[9 * f + 1], ec[9 * f + 2]];
    for (let i = 0; i < 3; i++) {
      if (g[i] <= floor[i]) continue;
      worst = Math.max(worst, rel(ac[9 * f + i], ec[9 * f + i], g[i], `G${i}${i} bin ${f}`));
      worst = Math.max(worst, rel(ap[3 * f + i], ep[3 * f + i], ep[3 * f + i], `p4[${i}] bin ${f}`));
      checked++;
    }
    for (const [c, i, j] of pairs) {
      if (g[i] <= floor[i] || g[j] <= floor[j]) continue;
      const den = Math.sqrt(g[i] * g[j]);
      worst = Math.max(worst, rel(ac[9 * f + c], ec[9 * f + c], den, `Re pair ${c} bin ${f}`));
      worst = Math.max(worst, rel(ac[9 * f + c + 1], ec[9 * f + c + 1], den, `Im pair ${c} bin ${f}`));
    }
  }
  assert(checked > NBINS, `${label}: too few bins above the floor (${checked})`);
  return { checked, worst };
}

/** Exact structural equality of two finish() results (typed arrays element-wise, NaN equal to NaN). */
function deepEqual(a, b, path = "result") {
  if (Object.is(a, b)) return;
  if (ArrayBuffer.isView(a) || Array.isArray(a)) {
    assert(ArrayBuffer.isView(b) || Array.isArray(b), `${path}: type differs`);
    assert(a.length === b.length, `${path}: length ${a.length} vs ${b.length}`);
    for (let i = 0; i < a.length; i++) if (!Object.is(a[i], b[i])) deepEqual(a[i], b[i], `${path}[${i}]`);
    return;
  }
  if (a && b && typeof a === "object" && typeof b === "object") {
    const ka = Object.keys(a).sort(), kb = Object.keys(b).sort();
    assertList(ka, kb, `${path} keys`);
    for (const k of ka) deepEqual(a[k], b[k], `${path}.${k}`);
    return;
  }
  throw new Error(`${path}: ${a} vs ${b}`);
}

// ----------------------------------------------------------------------------- building blocks

check("fir taps equal tests/vectors/fir_taps.json exactly", () => {
  const j = json("fir_taps.json");
  for (const [m, taps, len] of [[4, TAPS4, 209], [2, TAPS2, 105]]) {
    const exp = j[String(m)];
    assertEq(len, taps.length, `m=${m} length`);
    assertEq(exp.length, taps.length, `m=${m} json length`);
    const eb = new Float64Array(exp), ab = new Uint32Array(taps.buffer, taps.byteOffset, taps.length * 2);
    const ebb = new Uint32Array(eb.buffer);
    for (let i = 0; i < ebb.length; i++) assert(ebb[i] === ab[i], `m=${m} tap ${i >> 1} bits differ`);
  }
  return "209 + 105 taps, bit-identical";
});

check("decimator matches decimate_anchored (decimate_case.json, 1e-11)", () => {
  const j = json("decimate_case.json");
  let worst = 0;
  for (const c of j.cases) {
    const got = [];
    const d = new AnchoredDecimator(c.m, (idx, a, b, z) => got.push([idx, a, b, z]));
    j.x.forEach((v, r) => d.push(c.i0 + r, v[0], v[1], v[2]));
    assertEq(c.y.length, got.length, `m=${c.m} count`);
    assertEq(c.j0, got[0][0], `m=${c.m} j0`);
    for (let r = 0; r < c.y.length; r++) {
      assertEq(c.j0 + r, got[r][0], `m=${c.m} index row ${r}`);
      for (let a = 0; a < 3; a++) {
        const e = Math.abs(c.y[r][a] - got[r][a + 1]);
        worst = Math.max(worst, e);
        assert(e <= 1e-11, `m=${c.m} row ${r} axis ${a}: ${got[r][a + 1]} vs ${c.y[r][a]}`);
      }
    }
  }
  return `worst abs error ${worst.toExponential(2)}`;
});

check("fft matches direct DFT (1e-9)", () => {
  let seed = 5;
  const rnd = () => { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648 * 2 - 1; };
  const xr = new Float64Array(NFFT).map(rnd), xi = new Float64Array(NFFT).map(rnd);
  const re = xr.slice(), im = xi.slice();
  new Fft(NFFT).transform(re, im);
  let worst = 0;
  for (const k of [0, 1, 2, 17, 511, 1024, 1500, NFFT - 1]) {
    let sr = 0, si = 0;
    for (let t = 0; t < NFFT; t++) {
      const a = -2 * Math.PI * ((k * t) % NFFT) / NFFT;
      sr += xr[t] * Math.cos(a) - xi[t] * Math.sin(a);
      si += xr[t] * Math.sin(a) + xi[t] * Math.cos(a);
    }
    worst = Math.max(worst, Math.abs(sr - re[k]), Math.abs(si - im[k]));
  }
  assert(worst < 1e-9, `fft error ${worst}`);
  return `worst ${worst.toExponential(2)}`;
});

check("grid resampler reproduces numpy.interp rules", () => {
  const out = [];
  const g = new GridResampler(200.0, (i, x) => out.push([i, x]));
  g.push(0.0012, 1, 0, 0); g.push(0.0050, 2, 0, 0); g.push(0.0123, 3, 0, 0); g.push(0.0151, 4, 0, 0);
  g.finish();
  assertList([1, 2, 3], out.map((o) => o[0]), "indices");
  assertEq(2.0, out[0][1], "grid 1");
  assertClose(2.0 + (0.010 - 0.0050) / (0.0123 - 0.0050), out[1][1], 1e-12, "grid 2");
  assertClose(3.0 + (0.015 - 0.0123) / (0.0151 - 0.0123), out[2][1], 1e-12, "grid 3");
  const g2 = new GridResampler(200.0, () => {});
  g2.push(1.0, 0, 0, 0);
  assert(!g2.push(1.0, 0, 0, 0), "repeated time accepted");
});

check("levelling puts gravity on z", () => {
  const g = [0.3, -0.5, 9.78];
  const r = levelRotation(g);
  const dot = (row) => row[0] * g[0] + row[1] * g[1] + row[2] * g[2];
  assertClose(Math.hypot(...g), dot(r[2]), 1e-12, "gz");
  assertClose(0, dot(r[0]), 1e-12, "gx");
  assertClose(0, dot(r[1]), 1e-12, "gy");
});

check("toBase64LE: 1.0f is AACAPw==, special values round-trip", () => {
  assertEq("AACAPw==", toBase64LE(new Float32Array([1])), "1.0f");
  const v = new Float32Array([1.5, -2.25e-12, 0, 1.401298464324817e-45, 3.4e38]);
  const back = fromBase64LE(toBase64LE(v));
  assertList(Array.from(v), Array.from(back), "round trip");
  for (const n of [0, 1, 2, 3, 4, 5]) {
    const a = new Float32Array(n).map((_, i) => i * 0.37 - 1);
    assertList(Array.from(a), Array.from(fromBase64LE(toBase64LE(a))), `length ${n}`);
  }
});

check("toBase64LE round trip against stream_a_expected.json base64", () => {
  const e = json("stream_a_expected.json");
  let n = 0;
  for (const b of ["L", "M", "H"]) {
    for (const key of ["csd", "p4"]) {
      const s = e.bands[b][key];
      const back = toBase64LE(fromBase64LE(s));
      assert(back === s, `band ${b} ${key}: re-encoded base64 differs`);
      n += s.length;
    }
  }
  return `${n} base64 characters identical`;
});

// ----------------------------------------------------------------------------- streams

const worstTable = [];
const streams = {};

for (const name of ["stream_a", "stream_b", "stream_c"]) {
  let exp, s, r;
  try {
    exp = json(`${name}_expected.json`);
    s = loadStream(`${name}.csv.gz`, exp.meta.t0, exp.meta.lsb);
    const p = new SessionProcessor();
    feed(p, s);
    r = p.finish();
    streams[name] = { s, r };
  } catch (e) {
    report(false, `${name} load and process`, e.message);
    continue;
  }

  check(`${name} session scalars (status, counts, rates, anchors, gate, flags, end)`, () => {
    assertEq(exp.status, r.status, "status");
    assertEq(exp.n_samples, r.nRaw, "n_samples");
    assertEq(exp.fs_g, r.fsGrid, "fs_g");
    assertClose(exp.fs_probe, r.fsProbe, 1e-9, "fs_probe");
    assertClose(exp.fs_raw, r.fsRaw, 1e-9, "fs_raw");
    assertClose(exp.duration, r.duration, 1e-9, "duration");
    assertEq(exp.t_start, r.tStart, "t_start");
    assertEq(exp.j50, r.j50, "j50");
    assertEq(exp.n50, r.n50, "n50");
    assertEq(exp.nsec, r.nSeconds, "nsec");
    assertList(exp.flagged, r.flaggedSeconds, "flagged");
    assertEq(exp.end_second, r.endSecond, "end_second");
    assertClose(exp.rms_med, r.rmsMedian, 1e-9 * exp.rms_med, "rms_med");
    for (let a = 0; a < 3; a++) assertClose(exp.g_vec[a], r.gLevel[a], 1e-10, `g_vec[${a}]`);
    assertClose(exp.accept_fraction, r.acceptFraction, 1e-12, "accept_fraction");
    return `status=${r.status} fsGrid=${r.fsGrid} nSeconds=${r.nSeconds} flagged=${r.flaggedSeconds.length} endSecond=${r.endSecond}`;
  });

  for (const band of ["L", "M", "H"]) {
    check(`${name} band ${band} (k, n_total, windows, csd, p4)`, () => {
      const e = exp.bands[band];
      const got = r.bands[band];
      assertEq(e.k, got.k, "k");
      assertEq(e.n_total, got.nTotal, "n_total");
      assertList(e.windows, got.windows, "windows");
      const res = compareBand(`${name} ${band}`, fromBase64LE(e.csd), got.csd, fromBase64LE(e.p4), got.p4);
      worstTable.push({ name, band, k: got.k, worst: res.zeros ? null : res.worst, checked: res.checked });
      return res.zeros ? `k=${got.k}/${got.nTotal}, no accepted windows (all zeros)`
        : `k=${got.k}/${got.nTotal}, ${res.checked} diagonal bins, worst relative error ${res.worst.toExponential(3)}`;
    });
  }
}

// ----------------------------------------------------------------------------- non-destructive finish

for (const name of ["stream_a", "stream_b", "stream_c"]) {
  if (!streams[name]) continue;
  check(`${name} finish() is non-destructive (snapshots at 5 s, every 60 s and at half)`, () => {
    const { s, r } = streams[name];
    const p = new SessionProcessor();
    const half = Math.floor(s.n / 2);
    let snap = null, nSnaps = 0;
    const seen = new Set();
    let nextSnap = s.t[0] + 5;
    for (let i = 0; i < s.n; i++) {
      p.push(s.t[i], s.x[i], s.y[i], s.z[i]);
      if (i === half - 1 || s.t[i] >= nextSnap) {
        const before = p.status;
        const f = p.finish();
        assertEq(before, p.status, "live status changed by finish()");
        seen.add(before);
        if (i === half - 1) snap = f;
        nSnaps++;
        if (s.t[i] >= nextSnap) nextSnap = s.t[0] + 60 * (Math.floor((s.t[i] - s.t[0]) / 60) + 1);
      }
    }
    const half_ = half;
    const st = p.stats();
    const f1 = p.finish();
    const f2 = p.finish();
    deepEqual(r, f1);
    deepEqual(f1, f2, "second finish");
    assertEq(r.status === "complete" ? "running" : r.status, st.status, "live status before finish");
    return `${nSnaps} snapshots while ${[...seen].join("/")}, half-way snapshot status=${snap.status}; ` +
      `final result identical to a run without snapshots (sample ${half_} of ${s.n})`;
  });
}

check("stats() snapshot shape", () => {
  const p = new SessionProcessor();
  const st0 = p.stats();
  assertEq("probing", st0.status, "initial status");
  assertEq(false, p.ended, "ended");
  const { s } = streams.stream_c;
  feed(p, s, 0, Math.floor(s.n / 2));
  const st = p.stats();
  for (const k of ["status", "nRaw", "fsProbe", "fsGrid", "seconds", "flaggedSeconds", "bands"]) assert(k in st, `missing ${k}`);
  for (const b of ["L", "M", "H"]) assert("k" in st.bands[b] && "nTotal" in st.bands[b], `bands.${b}`);
  assertEq("running", st.status, "status");
  return JSON.stringify(st);
});

console.log("");
console.log("worst relative error per vector and band:");
for (const w of worstTable) {
  console.log(`  ${w.name} ${w.band}: ${w.worst === null ? "no accepted windows" : w.worst.toExponential(3)} (k=${w.k}, ${w.checked} diagonal bins)`);
}
console.log(failures === 0 ? "ALL PASS" : `${failures} FAILED`);
process.exit(failures === 0 ? 0 : 1);
