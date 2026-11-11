import SwiftUI

@main
struct QuakeScoreMeasureApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}

struct ContentView: View {
    @StateObject private var session = MeasureSession()
    @State private var minutes = 45

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("Measure now").font(.title).bold()
            Text("Place the phone flat on a charger, start, and leave it untouched with the app open. " +
                 "The screen stays on; lower its brightness. Nothing is stored or uploaded in this build.")
                .font(.body)
            Stepper("Duration: \(minutes) min", value: $minutes, in: 30...60, step: 5)
            switch session.state {
            case .idle, .finished:
                Button("Start session") { session.start(minutes: minutes) }
                    .buttonStyle(.borderedProminent)
            case .running:
                Button("Stop") { session.stop() }
                    .buttonStyle(.bordered)
            }
            Text("Samples: \(session.samples)")
            Text(String(format: "Measured rate: %.2f Hz", session.measuredRate))
            Text(String(format: "Elapsed: %.0f s", session.elapsed))
            if case .finished(let reason) = session.state {
                Text("Finished: \(reason)").foregroundColor(.secondary)
            }
            Spacer()
        }
        .padding()
    }
}
