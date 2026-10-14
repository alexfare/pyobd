import SwiftUI

struct ContentView: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "car.side")
                .font(.system(size: 52, weight: .semibold))
                .foregroundStyle(.tint)

            Text("pyOBD Mobile")
                .font(.largeTitle.bold())

            Text("iOS development has started.")
                .foregroundStyle(.secondary)
        }
        .padding()
    }
}
