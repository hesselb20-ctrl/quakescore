# QuakeScore Android collector

**Status: compiles and passes its tests; not yet run on a phone.**

- `:dsp-core:test`: 9 of 9 tests pass. The compiled Kotlin signal processing reproduces the Python
  reference on both streaming test vectors, in all three bands, to about 5e-7 relative.
- `:app:assembleDebug`: builds a debug APK (about 3.3 MB). The app code compiled without changes; one
  bookkeeping fix was needed in `dsp-core` (samples arriving after a session ends are now counted, as
  the reference does).
- `:app:lintDebug`: 0 errors, 21 warnings (untranslated text literals and dependency-version notes).
- Never installed or run on a device. Sensor delivery, batching, the foreground service, the wake
  lock, time sync, the barometer and battery cost are all untested in practice.

Built with JDK 17 (Temurin 17.0.21), Gradle 8.10.2, Android Gradle Plugin 8.7.3, Kotlin 2.0.21,
compile SDK 35, build tools 34.0.0.

## Build

1. Install JDK 17 and the Android SDK (platform 35), or Android Studio (Ladybug or later).
2. Create `android/local.properties` with one line, using forward slashes:
   `sdk.dir=C:/Users/<you>/AppData/Local/Android/Sdk`
3. From `android/`: `gradlew.bat :dsp-core:test :app:assembleDebug` (Linux and macOS: `./gradlew`).
   The tests read `../tests/vectors`. Regenerate the vectors and `FirTaps.kt` with
   `python experiments/export_device_vectors.py` from the repository root (with `PYTHONPATH=.`).
4. The APK is written to `app/build/outputs/apk/debug/app-debug.apk`.

On Windows, build from a short path. Android builds create deep folders, and a checkout under a long
path runs into the 260-character limit. A directory junction is enough:
`mklink /J C:\qs <path to the repository>`, then build from `C:\qs\android`.

## First test night without a server

The debug build has a field-test path, so no server is needed.

1. Install: `adb install app/build/outputs/apk/debug/app-debug.apk`.
2. Open the app, opt in, and on the "Your building" screen type a short name under "Field test" and
   press "Use as test building". Enter the floor by hand.
3. Leave the phone flat on a hard surface, on its charger, screen off, overnight. The notification
   shows when it is recording.
4. Next day, copy the session files off the phone (from cmd or Git Bash, not PowerShell):
   `adb exec-out run-as org.quakescore.collector tar c files/sessions > sessions.tar`
   then `tar xf sessions.tar`.
5. Look at them: `python experiments/inspect_sessions.py files/sessions`. It prints, per session, the
   windows kept and the measured noise floor of the phone, and every candidate peak with its label.

Uploads to the placeholder server address fail and are retried; the session files stay on the phone
until an upload succeeds. To record battery cost, note the battery percentage before and after a
night on battery (see `docs/validation_protocol.md`).

## Layout

```
android/
  settings.gradle.kts, build.gradle.kts, gradle.properties, gradle/wrapper/gradle-wrapper.properties
  dsp-core/                   pure Kotlin/JVM, no Android imports
    src/main/kotlin/org/quakescore/dsp/
      Spec.kt                 NFFT, HOP, NBINS, bands, StreamConfig
      FirTaps.kt              GENERATED: decimation filters (factor 4: 209 taps, factor 2: 105 taps)
      GridResampler.kt        epoch-anchored linear interpolation (numpy.interp rules)
      AnchoredDecimator.kt    streaming decimate_anchored
      Levelling.kt            level_rotation, median
      Fft.kt                  iterative radix-2 complex FFT
      BandAccumulator.kt      2048-point windows, CSD and |X|^4 sums, tier B extension point
      SessionProcessor.kt     the streaming pipeline and gate (rules documented at the top)
      Packing.kt              float32 little-endian base64
      TimeBase.kt             sensor clock -> UTC, linear offset and drift fit
    src/test/kotlin/...       JUnit 4 tests against tests/vectors
  app/                        the Android application (plain Views, no XML layouts)
    src/main/java/org/quakescore/collector/
      ConsentActivity, MainActivity, BuildingPickActivity, FloorSetupActivity, SettingsActivity
      RecordingService        foreground service: conditions, stillness probe, session
      StillnessDetector       2-minute flat-and-still check at a low rate
      SessionRecorder         events -> TimeBase -> SessionProcessor; barometer, battery
      TimeSync, Sntp          GNSS / SNTP / wall-clock sync points
      Footprints, Locations   footprint parsing, point-in-polygon, nearest edge; one location fix
      Floor                   barometric floor
      SessionJson, SessionStore, Workers (upload, deletion, delete-and-stop), Api, Prefs, Ui
```

## Unit tests and tolerance

`./gradlew :dsp-core:test` runs:

- `firTapsAreBitIdenticalToPython`: `FirTaps.kt` against `tests/vectors/fir_taps.json`, bit for bit.
- `decimatorMatchesDecimateAnchored`: streaming decimator against `decimate_anchored` (1e-11 absolute).
- `streamA_200HzGrid_withTransient`: ~10 min at ~198.4 Hz (two tones plus noise plus tilted gravity,
  quantised to 0.0012 m/s^2, 20 us timestamp jitter, a 2 s burst that flags 3 seconds).
- `streamB_100HzGrid_endsOnFlaggedRun`: ~25 min at ~99.6 Hz (100 Hz grid, factor-2 filter, band L
  windows, a tilt step that ends the session through the 60 s flagged-run rule).
- FFT against a direct DFT, the grid interpolation rules, levelling, packing, and the time base.

Exact equality is required for counts, anchor indices, flagged seconds, session end and the indices of
accepted windows. Accumulators (mean CSD and mean |X|^4) must agree to a relative error of 2e-5
(float32 level): diagonal terms and p4 relative to themselves, off-diagonal terms relative to
sqrt(Gii Gjj), on bins above the noise floor (Gii > 1e-4 x the band median of Gii).

## Design notes

**Streaming equivalent of the reference.** `quakescore/device/pipeline.py` uses whole-session
statistics; the device uses a 120 s warm-up (gravity, levelling, median RMS, then frozen), flags
seconds above 5x the warm-up median RMS or tilted more than 0.0035 rad, drops windows overlapping a
flagged second, and ends the session after more than 60 consecutive flagged seconds. The grid rate is
chosen from the first 10 s. Full rules at the top of `SessionProcessor.kt` and in `docs/platforms.md`.

**Foreground service type `specialUse`.** Explained at the top of `RecordingService.kt`: `health`
needs a health use case and permissions, `dataSync` is limited to 6 h per 24 h on Android 15,
`location` is not used. The service runs while opted in, uses no sensors while waiting, and records
when: setup complete, charging (unless on-battery is allowed), screen off, inside the night window
(default 23:00-07:00), and the phone flat within 15 degrees and still for 2 minutes. Sessions use
`TYPE_ACCELEROMETER` at 5000 us with 10 s batching and a partial wake lock held only while recording,
and end on movement, unplugging (unless allowed) or after 8 hours. The still thresholds in
`StillnessDetector` are provisional and to be measured (method in that file).

**Time base.** GNSS time from an existing GPS fix, the Android 13+ GNSS clock, SNTP (pool.ntp.org),
else wall clock (`sync_source` "none", `sync_sigma_ms` -1). Sampled at start, every 10 min and at the
end; offset and drift fitted linearly (`TimeBase`).

**Building pick: rounded position instead of an H3 cell.** The phone takes one location fix in the
foreground, keeps it on the device, and requests `GET {base}/v1/footprints?lat=..&lon=..` with the
position rounded to 0.01 degrees. It snaps to the nearest footprint (point in polygon, else nearest
edge) and lists the five nearest for confirmation. Only the building id is uploaded with sessions.
Choice and trade-off: `com.uber:h3` ships native JNI libraries and adds APK size and a native loading
path that would need testing on many devices. A 0.01 degree cell (about 1.1 km by 0.7 km at 50 degrees
latitude) reveals about as much as an H3 resolution-8 cell (about 0.7 km^2): in both cases the server
learns the neighbourhood of the person at setup time, not the building. Differences: the server sees a
rounded point it could map to H3 itself; it should return footprints within 0.01 degrees on each side
of that point so a building near the cell edge is not missed, which makes the response larger. The
request is not linked to uploads (no id is sent), but it does come from the phone's IP address.
The confirmed fix (rounded to about 10 m) stays on the phone for the place check: when the app is
opened (at most every 12 h) it takes one fix, and if that is more than 150 m from the confirmed place,
recording pauses until the user confirms the building again. There is no background location
permission, so this check only happens when the app is opened.

**Floor.** Barometer: entrance (ground level) then resting spot during setup, floor = round(dh / 3.2 m)
with dh = 8434 m ln(p_ground / p) (temperature-scaled if an ambient sensor exists), `baro_entry`. The
session median pressure is used against the entrance reading only if that is under 3 h old (weather);
otherwise the setup estimate is kept. Manual entry otherwise (`manual`). Both value and method are kept.

**Upload.** WorkManager, unmetered network and charging by default (Settings can change both),
exponential backoff, the local file is deleted after a 2xx. Only the final feature JSON is stored, in
app-private storage; raw samples never leave RAM. Sessions with no accepted window are not uploaded.

**Delete my contributions and stop.** Stops the service, cancels uploads, deletes all local session
files, queues `DELETE {base}/v1/sessions/{id}` for every uploaded session id (the server must implement
it), and wipes all settings including the install secret.

**Tier B sync frames: not in v1.** The extension point is `WindowSpectraSink` /
`BandAccumulator.tierBSink` in dsp-core, called for every accepted window with its float32 spectra. A
v2 would keep the server-hinted frequency ranges of bands L and M (DESIGN.md 3.1 item 9), add an opt-in
toggle, and add a `frames` field to the schema.

## Upload schema v1

`POST {base}/v1/sessions`, gzip JSON (`Content-Encoding: gzip`). `session_id` is an idempotency key.

```json
{
  "schema": 1,
  "session_id": "uuid4",
  "building_id": "osm:way/123",
  "contributor": "first 16 hex chars of SHA-256(install_secret || building_id)",
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
  "platform": "android",
  "app_version": "0.1.0",
  "bands": {
    "L": {"k": 12, "csd": "base64", "p4": "base64"},
    "M": {"k": 150, "csd": "base64", "p4": "base64"},
    "H": {"k": 900, "csd": "base64", "p4": "base64"}
  }
}
```

Values are placeholders showing types. `install_secret`: 32 random bytes created at install, never
uploaded; `building_id` appended as UTF-8. `t_start`: UTC epoch seconds rounded to the minute.
`lsb`: `Sensor.getResolution()` in m/s^2. `sync_sigma_ms`: -1 when `sync_source` is "none". `temp_c`:
battery temperature or null. `csd`: base64 of little-endian float32[1025 * 9], per bin
`[Gxx, Gyy, Gzz, Re Gxy, Im Gxy, Re Gxz, Im Gxz, Re Gyz, Im Gyz]`, G the mean (sum / k) one-sided CSD in
(m/s^2)^2/Hz with `G_ij = mean(X_i conj(X_j))`. `p4`: base64 of little-endian float32[1025 * 3], mean
|X_i|^4 for x, y, z. Axes are the levelled frame (z vertical). A band with k = 0 carries zeros.

## Dependencies and licences

App: AndroidX core, activity, lifecycle, WorkManager (Apache-2.0), kotlinx-coroutines (Apache-2.0),
OkHttp (Apache-2.0); JSON via the platform `org.json`. dsp-core has no runtime dependency. Test only:
JUnit 4 (EPL-1.0, not shipped) and kotlinx-serialization-json (Apache-2.0).

## To be measured on devices

Real sampling rates and timestamp regularity per model, still/flat thresholds, battery cost of a
session, which manufacturers stop the service, SNTP availability with the screen off, barometric floor
accuracy. How to measure each is described in `docs/platforms.md`.
