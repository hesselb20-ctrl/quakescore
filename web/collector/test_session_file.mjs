// End-to-end check of the session file: a recorded-style stream goes through the JavaScript
// processor and the session-file builder, and the result is written to disk for the Python codec.
// Usage: node web/collector/test_session_file.mjs <output folder>
import { gunzipSync } from "node:zlib";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { SessionProcessor } from "./dsp.js";
import { LsbTracker, buildPayload, fileName, noiseFloorUg } from "./session_file.js";

const here = dirname(fileURLToPath(import.meta.url));
const vectors = join(here, "..", "..", "tests", "vectors");
const out = process.argv[2];
if (!out) { console.error("usage: node test_session_file.mjs <output folder>"); process.exit(2); }
mkdirSync(out, { recursive: true });

let failed = 0;
for (const name of ["stream_c", "stream_b"]) {
  const exp = JSON.parse(readFileSync(join(vectors, `${name}_expected.json`), "utf8"));
  const { t0, lsb } = exp.meta;
  const proc = new SessionProcessor();
  const tracker = new LsbTracker();
  let off = 0;
  for (const line of gunzipSync(readFileSync(join(vectors, `${name}.csv.gz`))).toString("utf8").split("\n")) {
    if (!line.trim()) continue;
    const f = line.split(",");
    off += Number(f[0]);
    const x = Number(f[1]) * lsb, y = Number(f[2]) * lsb, z = Number(f[3]) * lsb;
    tracker.push(x, y, z);
    proc.push(t0 + off * 1e-9, x, y, z);
  }
  const result = proc.finish();
  const payload = buildPayload(result, {
    sessionId: name === "stream_c" ? "3f2b8c1e-7a4d-4e6f-9b1a-2c5d8e7f6a10" : "9a1c4e7b-2d5f-4a8c-b3e6-1f4a7d0c9b25",
    buildingId: "test:vector-check", contributor: "0123456789abcdef", phoneModel: "iPhone (browser)", floor: 3,
    charging: true, platform: "ios", lsb: tracker.value, batteryStart: null, batteryEnd: null,
  });
  writeFileSync(join(out, fileName(payload)), JSON.stringify(payload));
  const lsbOk = Math.abs(tracker.value / lsb - 1) < 1e-6;
  const noise = noiseFloorUg(result);
  if (!lsbOk) failed++;
  console.log(`${lsbOk ? "PASS" : "FAIL"} ${name}: status=${result.status} k=${payload.bands.L.k}/${payload.bands.M.k}/${payload.bands.H.k} ` +
    `fs_raw=${payload.fs_raw.toFixed(3)} lsb estimate=${tracker.value.toExponential(3)} (true ${lsb}) noise=${noise == null ? "n/a" : noise.toFixed(1)} ug/rtHz -> ${fileName(payload)}`);
}
process.exit(failed ? 1 : 0);
