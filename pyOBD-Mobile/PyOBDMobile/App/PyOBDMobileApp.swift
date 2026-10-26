import SwiftUI

@main
struct PyOBDMobileApp: App {
    @Environment(\.scenePhase) private var scenePhase
    @StateObject private var connection = ConnectionManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(connection)
                .onChange(of: scenePhase) { _, newPhase in
                    connection.scenePhaseChanged(newPhase)
                }
        }
    }
}
