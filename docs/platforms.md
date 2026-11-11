# Platforms: Android, iOS and the browser

The spectral contract (DESIGN.md 3.1) is the same on both platforms: the same grid, privacy filter,
zoom bands, windows, gate rules and upload schema. What differs is when a phone may measure, how fast
and how regularly it samples, which clocks and sensors exist, and what the user has to do.

Status: the Android app (`android/`) compiles and its signal processing passes the reference tests, but it has not been run on a phone. The iOS
app (`ios/`) is a "measure now" skeleton without the spectral pipeline. A browser collector
(`web/collector/`) runs the full pipeline in a web page and is the way to record on an iPhone today;
it was checked with simulated sensor readings and has not run on a phone either. No number in this
document was measured on a device; wherever one is needed it says "to be measured" and how.

## Summary

| Topic | Android | iOS |
|---|---|---|
| Mode | Unattended: records whenever the conditions hold | "Measure now": the user starts a 30-60 min session |
| Background sensor access | Foreground service (type `specialUse`) with a notification | Not available for the accelerometer; app must stay in the foreground |
| Screen during a session | Off | On (idle timer disabled), dimmed by the user |
| Requested rate | 200 Hz (5000 us), batched | 100 Hz (`accelerometerUpdateInterval = 0.01`) |
| Grid | 200 Hz if the measured rate is >= 190 Hz, else 100 Hz | expected 100 Hz grid (to be measured per model) |
| Batching | `maxReportLatencyUs` (10 s) into the sensor FIFO | None in the API; updates arrive on an OperationQueue |
| Sensor time base | `SensorEvent.timestamp`, elapsed-realtime nanoseconds | `CMLogItem.timestamp`, seconds since boot (uptime base) |
| UTC sources | GNSS time from an existing GPS fix, GNSS clock (Android 13+), SNTP, else wall clock | SNTP (to be written), else wall clock |
| Barometer | `Sensor.TYPE_PRESSURE` (hPa) | `CMAltimeter` relative altitude (m) and pressure (kPa) |
| Battery | `BatteryManager` percent, plugged state, battery temperature | `UIDevice.batteryLevel`, `batteryState`; no battery temperature (`temp_c` null) |
| Location for the building pick | One foreground fix (fine or coarse) | One foreground Core Location fix ("when in use") |
| Upload | WorkManager, unmetered + charging by default | URLSession background transfer (to be written) |

## Background sensor access

**Android.** A foreground service may read the accelerometer with the screen off as long as it shows a
notification. Android 14 requires a declared service type. `health` needs health permissions and a
health use case, `dataSync` is for data transfer and is limited to 6 hours per 24 hours on Android 15,
`location` and `connectedDevice` do not apply, so the service is `specialUse` with a subtype
explanation in the manifest (Google Play reviews it). A partial wake lock is held only while recording,
so the CPU keeps draining the sensor FIFO when the screen is off. The service is started from the app
(foreground) or at boot (an allowed exemption from the background-start limits). It uses no sensors
while it waits. Some manufacturers stop background services more aggressively than stock Android; the
user may have to exempt the app from battery optimisation. Which models do this is to be measured: run
the app overnight on each model and check `accept_fraction` and session durations.

**iOS.** There is no API that lets a third-party app read the accelerometer unattended in the
background at these rates. A session therefore runs with the app in the foreground, the screen on and
the idle timer disabled (`UIApplication.isIdleTimerDisabled`). If the user locks the phone or switches
app, updates stop and the session ends. `CMSensorRecorder` records accelerometer data while the app is
not running, but the system then stores raw samples on the device before the privacy filter can be
applied, which the privacy contract (no raw samples on disk) excludes; it is not used.

## Sampling rates and regularity

**Android.** The app requests 5000 us (200 Hz). Since Android 12, apps without
`HIGH_SAMPLING_RATE_SENSORS` are capped at 200 Hz, so the permission is not requested. The delivered
rate is rarely the nominal one; dsp-core measures it over the first 10 s to pick the grid and reports
the session mean as `fs_raw`. Timestamp jitter and gaps differ by model. To be measured per model: the
distribution of timestamp intervals, the rate in `fs_raw` and the share of rejected (non-increasing)
timestamps, from a 30 minute recording with a debug build that logs these counters (never the samples).

**iOS.** `CMMotionManager` accepts an update interval; the delivered rate is hardware dependent and is
to be measured the same way (the skeleton shows the measured rate live). A rate below 190 Hz selects
the 100 Hz grid and the factor-2 privacy filter, which tests/vectors/stream_b covers.

Both platforms: the interpolation droop sinc^4(f / fs_raw) in power is corrected on the server from
`fs_raw` (`quakescore/features.py` `droop`).

## Batching

**Android.** `registerListener(..., samplingPeriodUs = 5000, maxReportLatencyUs = 10 s)` lets the sensor
hub buffer events; the FIFO size decides the real latency and may force earlier delivery. Events keep
their own timestamps, so batching does not change the result. Batching lowers wake-ups, but because a
wake lock is held during a session the battery saving is limited; the cost is to be measured (below).

**iOS.** No batching control. The app is in the foreground, so updates arrive continuously.

## Time synchronisation

UTC stamps matter mainly for tier B (cross-phone sync frames) and for anchoring the grid; tier A
spectra are insensitive to offsets of seconds.

**Android.** Sensor timestamps use the elapsed-realtime base (the app checks the first event and drops
the session if the base differs by more than 120 s). Sync points are taken at session start, every
10 minutes and at the end: GNSS time from a GPS fix the system already holds
(`Location.getTime()` paired with `getElapsedRealtimeNanos()`; only the time fields are read, the app
never requests a fix for this, and without background-location permission this normally yields
nothing with the screen off), the platform GNSS clock on Android 13+, else SNTP to pool.ntp.org (best
of four, uncertainty = delay / 2), else the wall clock (`sync_source` "none", `sync_sigma_ms` -1).
`TimeBase` fits offset and drift linearly. The mapping actually applied to samples is continuous: it
slews towards the latest fit over 10 minutes (at most 200 ppm), and the reported uncertainty includes
the largest difference between the applied mapping and the final fit. While charging the phone does
not enter Doze, so SNTP works at night; on battery a foreground service keeps network access, but this
is to be verified per model.

**iOS.** `CMLogItem.timestamp` is seconds since boot on the uptime clock, which stops while the device
sleeps; during a foreground session the device does not sleep. There is no GNSS time API, so the plan
is SNTP over the Network framework against `ProcessInfo.systemUptime`, with the same fit. The skeleton
uses the wall clock only.

## Barometer and floor

**Android.** `Sensor.TYPE_PRESSURE` gives hPa. Setup records the median pressure over 10 s at the
entrance (ground level) and again at the resting spot; floor = round(dh / 3.2 m) with
dh = 8434 m * ln(p_ground / p) scaled by (273.15 + T) / 288.15 when an ambient temperature sensor
exists (`floor_method` "baro_entry"). During a session the median pressure is recorded; it is compared
with the entrance reading only if that reading is less than 3 hours old, because weather changes
pressure by amounts equivalent to several storeys over a day; otherwise the setup estimate is used.
Without a barometer, or if the user overrides, `floor_method` is "manual". The method "baro_ref"
(against a ground-floor reference phone, DESIGN.md 3.2) is reserved for the server and is not produced
by the app.

**iOS.** `CMAltimeter.startRelativeAltitudeUpdates` reports altitude change in metres since the start
of updates and pressure in kPa. Starting it at the entrance and reading it at the resting spot gives dh
directly ("baro_entry"), provided the app stays open between the two.

The per-device accuracy of both methods is to be measured: walk known storeys in a building with
surveyed floor heights and compare.

## Battery

**Android.** Battery percent (`BATTERY_PROPERTY_CAPACITY`) at start and end, whether the phone stayed
on external power for the whole session, and battery temperature (`EXTRA_TEMPERATURE`) go into every
upload. Sessions run on charge by default, so start/end percentages do not show the cost.

**iOS.** `UIDevice.batteryLevel` (enable `isBatteryMonitoringEnabled`) and `batteryState`. Its
granularity is to be checked on devices. iOS exposes no battery temperature; `temp_c` is null.

**Energy cost: to be measured.** Android: enable "also record when not charging", run 2-hour sessions
on a full battery with the screen off and compare against 2 hours idle on the same phone (battery
percent and `adb shell dumpsys batterystats`), per model. iOS: the screen dominates; measure a 60
minute session at minimum brightness with Xcode's energy gauge or with battery level before and after.

## What the user must do

**Android.** Once: read the consent screen and opt in, allow notifications (Android 13+), allow
location once to pick the building, confirm the building from the list of five, and set the floor
(walk from the entrance to the resting spot, or type it). Then nothing: put the phone flat on a charger
at night with the screen off. Optionally exempt the app from battery optimisation if the phone's
manufacturer stops background services. Reopen the app after moving house; a fix more than 150 m from
the confirmed place asks for the building again.

**iOS.** Each session: open the app, put the phone flat on a charger, start a 30-60 minute session,
dim the screen and leave the app open and the phone untouched.

## Browser collector

`web/collector/` is one static page. It needs no install and no server, which makes it the shortest
route to a first real night, on iPhone in particular.

- **Sensor.** `devicemotion` events, `accelerationIncludingGravity`, in m/s^2. Browsers deliver
  about 60 events a second (to be measured per phone), so the 100 Hz grid and the factor-2 privacy
  filter are used; `tests/vectors/stream_c` covers a 59.94 Hz input with timestamp jitter.
- **Permission.** iOS asks for motion access once, on a tap (`DeviceMotionEvent.requestPermission`).
  The page must be served over https.
- **Foreground only.** Events stop when the page is hidden or the phone locks. A gap of more than 2 s
  ends the session; a copy of the spectra so far is kept in the browser's local storage every minute.
  The page asks for a screen wake lock where the browser has one.
- **Time.** Event timestamps on the page clock (`performance.timeOrigin + event.timeStamp`), no
  synchronisation: `sync_source` "none", `sync_sigma_ms` -1. Good enough for tier A spectra, not for
  tier B.
- **Not available.** Barometer (floor is typed), battery temperature, and on iOS the battery level
  (`battery_start` and `battery_end` are null). `lsb` is estimated as the smallest step seen between
  readings. `sensor_name` is "devicemotion" and `app_version` starts with "web-".
- **Output.** The same upload schema v1, saved as a file by the user instead of uploaded.

Its signal processing (`web/collector/dsp.js`) is a port of `SessionProcessor.kt` and passes the same
vectors (`node web/collector/test_dsp.mjs`).

## Streaming gate rules (all platforms)

The Python reference (`quakescore/device/pipeline.py`) uses session-wide statistics. A phone cannot
hold a night of raw samples, so the device uses these streaming-equivalent rules
(`android/dsp-core/.../SessionProcessor.kt`; Python mirror `process_session_streaming` in
`experiments/export_device_vectors.py`, which writes the test vectors):

1. Grid rate from the first 10 s of raw samples: 200 Hz if the rate is >= 190 Hz, else 100 Hz.
2. Uniform epoch-anchored grid by linear interpolation, privacy FIR (pass 20 Hz, stop 25 Hz, 80 dB)
   and anchored decimation to 50 Hz, then factor-4 decimations to 12.5 and 3.125 Hz; output sample j
   sits at input index j*m.
3. Warm-up: the first 120 one-second blocks of the 50 Hz stream (the phone is already required to be
   still) give the gravity direction (component-wise median of block means), the median block RMS and
   the levelling gravity (mean of the unflagged warm-up block means). These are frozen.
4. A second is flagged if its RMS exceeds 5x the warm-up median RMS or its mean vector tilts more than
   0.0035 rad from the warm-up gravity. If the warm-up gravity is more than 15 degrees from vertical the
   session yields nothing.
5. A window (2048 samples, 50% overlap, window k starting at band sample 1024 k) is dropped if it
   overlaps any flagged second; long L and M windows are decided when they complete.
6. More than 60 consecutive flagged seconds end the session.
7. Accepted windows: mean removal, linear detrend, periodic Hann, FFT, scale sqrt(2 / (fs sum w^2));
   accumulate the 3x3 CSD, |X_i|^4 per axis, and the count.

## Upload schema v1

`POST {base}/v1/sessions`, body gzip-compressed JSON (`Content-Encoding: gzip`,
`Content-Type: application/json`). The server must treat `session_id` as an idempotency key (a client
retries when a reply is lost).

```json
{
  "schema": 1,
  "session_id": "uuid4",
  "building_id": "osm:way/123",
  "contributor": "16 hex chars: first 16 hex chars of SHA-256(install_secret || building_id)",
  "phone_model": "Manufacturer Model",
  "sensor_name": "string",
  "floor": 3,
  "floor_method": "baro_entry | baro_ref | manual",
  "t_start": 1793000000,
  "duration": 21600.0,
  "fs_raw": 198.4,
  "lsb": 0.0012,
  "sync_source": "gnss | ntp | none",
  "sync_sigma_ms": 12.5,
  "accept_fraction": 0.87,
  "temp_c": 27.5,
  "battery_start": 80,
  "battery_end": 82,
  "charging": true,
  "platform": "android | ios",
  "app_version": "0.1.0",
  "bands": {
    "L": {"k": 12, "csd": "base64", "p4": "base64"},
    "M": {"k": 150, "csd": "base64", "p4": "base64"},
    "H": {"k": 900, "csd": "base64", "p4": "base64"}
  }
}
```

The numbers above are placeholders showing types, not measurements.

- `install_secret` is 32 random bytes created at install and never uploaded; `building_id` is appended
  as UTF-8 bytes before hashing.
- `t_start` is UTC epoch seconds of the first sample rounded to the minute; `duration` in seconds.
- `fs_raw` is the measured raw rate (Hz); `lsb` is `Sensor.getResolution()` in m/s^2.
- `sync_sigma_ms` is -1 when `sync_source` is "none"; the server accepts -1 only in that case.
- `battery_start` and `battery_end` are null when the platform exposes no battery level.
- `temp_c` is battery temperature in degrees C, or null.
- `csd`: base64 of little-endian float32[1025 * 9]; per bin, in this order:
  `Gxx, Gyy, Gzz, Re Gxy, Im Gxy, Re Gxz, Im Gxz, Re Gyz, Im Gyz`, where G is the mean (sum divided by
  k) one-sided CSD in (m/s^2)^2/Hz with `G_ij = mean(X_i * conj(X_j))`.
- `p4`: base64 of little-endian float32[1025 * 3]; per bin, mean of |X_i|^4 for i = x, y, z.
- Axes are the levelled frame: z vertical, x the projection of the device x axis onto the horizontal
  plane, y = z cross x. Bin f of band b is at f * fs_b / 2048 Hz (fs = 3.125, 12.5, 50 Hz).
- A band with k = 0 carries zeros.

Other endpoints the app uses: `GET {base}/v1/footprints?lat=..&lon=..` (position rounded to 0.01
degrees; GeoJSON FeatureCollection with `properties.id` and optional `properties.name`,
`properties.addr`), `GET {base}/v1/buildings/{id}/public` (shown as text), and
`DELETE {base}/v1/sessions/{session_id}` for "delete my contributions" (not in the original API list;
the server needs to add it, with the random session id as the capability, so session ids must never
be published).

Tier B sync frames are not part of v1; a later schema version would add them per band.
