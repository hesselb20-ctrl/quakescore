// Renders the repository images: every .html file in this folder becomes docs/media/<name>.png.
//
// Usage: node docs/media/src/build.mjs [name ...]
// Needs Node 22 or newer and Chrome, Chromium or Edge. Set CHROME to the browser path if it is
// not found. The pages are served from a local web server because collector.html embeds the
// real collector page and drives it with simulated sensor readings.
import { spawn } from "node:child_process";
import { createServer } from "node:http";
import { existsSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, extname, join, normalize, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const SRC = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(SRC, "../../..");
const OUT = resolve(SRC, "..");
const WIDTH = 1600, HEIGHT = 900, SCALE = 2;
const TYPES = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".mjs": "text/javascript", ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml" };

function findBrowser() {
  const candidates = [
    process.env.CHROME,
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
  ];
  const hit = candidates.find((p) => p && existsSync(p));
  if (!hit) throw new Error("No browser found. Set CHROME to the path of Chrome, Chromium or Edge.");
  return hit;
}

const server = createServer((req, res) => {
  const path = normalize(join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname)));
  if (!path.startsWith(ROOT) || !existsSync(path) || !statSync(path).isFile()) { res.writeHead(404).end(); return; }
  res.writeHead(200, { "Content-Type": TYPES[extname(path)] || "application/octet-stream", "Cache-Control": "no-store" });
  res.end(readFileSync(path));
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const base = `http://127.0.0.1:${server.address().port}`;

const profile = mkdtempSync(join(tmpdir(), "qs-media-"));
const debugPort = 9400 + Math.floor(Math.random() * 400);
const browser = spawn(findBrowser(), ["--headless=new", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`,
  "--hide-scrollbars", "--no-first-run", "--disable-extensions", "about:blank"], { stdio: "ignore" });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function devtools(path, init) {
  for (let i = 0; i < 80; i++) {
    try { const r = await fetch(`http://127.0.0.1:${debugPort}${path}`, init); if (r.ok) return r.json(); } catch (e) { /* not up yet */ }
    await sleep(250);
  }
  throw new Error("The browser did not start.");
}

async function render(name) {
  const target = await devtools(`/json/new?about:blank`, { method: "PUT" });
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => { ws.onopen = r; });
  let id = 0; const pending = {}; const problems = [];
  ws.onmessage = (e) => {
    const m = JSON.parse(e.data);
    if (m.id && pending[m.id]) { pending[m.id](m); delete pending[m.id]; }
    if (m.method === "Runtime.exceptionThrown") problems.push(m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text);
  };
  const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending[i] = r; ws.send(JSON.stringify({ id: i, method, params })); });
  await send("Runtime.enable");
  await send("Emulation.setDeviceMetricsOverride", { width: WIDTH, height: HEIGHT, deviceScaleFactor: SCALE, mobile: false });
  await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "light" }] });
  await send("Page.navigate", { url: `${base}/docs/media/src/${name}.html` });
  let ready = false;
  for (let i = 0; i < 480 && !ready; i++) {
    await sleep(250);
    const r = await send("Runtime.evaluate", { expression: "window.__ready === true", returnByValue: true });
    ready = r.result?.result?.value === true;
  }
  await sleep(1300);                                   // let the last interface refresh land
  const shot = await send("Page.captureScreenshot", { format: "png" });
  writeFileSync(join(OUT, `${name}.png`), Buffer.from(shot.result.data, "base64"));
  ws.close();
  await fetch(`http://127.0.0.1:${debugPort}/json/close/${target.id}`).catch(() => {});
  console.log(`${name}.png${ready ? "" : "  (page never signalled ready)"}${problems.length ? "  errors: " + problems.join(" | ") : ""}`);
}

try {
  const names = process.argv.length > 2 ? process.argv.slice(2) : readdirSync(SRC).filter((f) => f.endsWith(".html")).map((f) => f.slice(0, -5));
  for (const name of names) await render(name);
} finally {
  browser.kill();
  server.close();
  await sleep(500);
  try { rmSync(profile, { recursive: true, force: true }); } catch (e) { /* the browser may still hold a file */ }
}
