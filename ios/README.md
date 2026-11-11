# QuakeScore iOS "measure now" (skeleton)

Status: a skeleton, not a collector. It has not been built or run.

`QuakeScoreMeasure/` contains two Swift files for a SwiftUI app (iOS 15+): a user-started 30-60 minute
foreground session with CMMotionManager accelerometer updates requested at 100 Hz, the idle timer
disabled, timestamps mapped to UTC and the sample rate measured. Samples are counted and discarded.
The spectral pipeline, time sync, floor, building pick, consent, deletion and upload are not
implemented; the TODO list at the end of `MeasureSession.swift` says what each needs.

To try it: create an iOS App project in Xcode (SwiftUI lifecycle), replace the generated files with
these two, and run on a device (the simulator has no accelerometer data). No Info.plist usage string is
needed for the accelerometer; a later building pick needs `NSLocationWhenInUseUsageDescription`.

Why iOS is "measure now" only, and every other platform difference: `docs/platforms.md`.
