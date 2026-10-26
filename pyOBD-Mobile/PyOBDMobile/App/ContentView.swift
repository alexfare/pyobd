import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var connection: ConnectionManager
    @State private var selectedSection: MobileSection = .overview

    var body: some View {
        TabView(selection: $selectedSection) {
            OverviewView(selectedSection: $selectedSection)
                .tag(MobileSection.overview)
                .tabItem { Label("Overview", systemImage: "car.fill") }

            LiveDataView()
                .tag(MobileSection.liveData)
                .tabItem { Label("Live Data", systemImage: "waveform.path.ecg") }

            DiagnosticsView()
                .tag(MobileSection.diagnostics)
                .tabItem { Label("Diagnostics", systemImage: "stethoscope") }

            ReadinessView()
                .tag(MobileSection.readiness)
                .tabItem { Label("Readiness", systemImage: "checklist") }

            ConnectionView()
                .tag(MobileSection.connection)
                .tabItem { Label("Connection", systemImage: "cable.connector") }
        }
        .onAppear { connection.setActiveSection(selectedSection) }
        .onChange(of: selectedSection) { _, section in
            connection.setActiveSection(section)
        }
    }
}

private struct OverviewView: View {
    @EnvironmentObject private var connection: ConnectionManager
    @Binding var selectedSection: MobileSection

    private let columns = [
        GridItem(.flexible(), spacing: 12),
        GridItem(.flexible(), spacing: 12),
    ]

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 18) {
                    ConnectionBanner { selectedSection = .connection }

                    VStack(alignment: .leading, spacing: 12) {
                        Text("Vehicle").font(.headline)
                        LabeledContent("VIN", value: connection.vehicleVIN)
                        LabeledContent("Protocol", value: connection.vehicleProtocol)
                        LabeledContent("Adapter voltage", value: connection.adapterVoltage)
                    }
                    .mobileCard()

                    LazyVGrid(columns: columns, spacing: 12) {
                        ForEach(connection.liveReadings.prefix(6)) { reading in
                            VStack(alignment: .leading, spacing: 8) {
                                Image(systemName: icon(for: reading.pid))
                                    .font(.title2)
                                    .foregroundStyle(.tint)
                                Text(reading.formattedValue)
                                    .font(.title3.weight(.semibold))
                                    .monospacedDigit()
                                Text(reading.pid.name)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(2)
                            }
                            .frame(maxWidth: .infinity, minHeight: 110, alignment: .leading)
                            .mobileCard()
                        }
                    }

                    if connection.liveReadings.isEmpty {
                        ContentUnavailableView(
                            "Waiting for vehicle data",
                            systemImage: "gauge.with.dots.needle.0percent",
                            description: Text("Connect an adapter to begin reading supported PIDs.")
                        )
                    }
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("pyOBD Mobile")
        }
    }

    private func icon(for pid: StandardPID) -> String {
        switch pid {
        case .engineRPM: "gauge.with.dots.needle.67percent"
        case .vehicleSpeed: "speedometer"
        case .coolantTemperature, .intakeTemperature: "thermometer.medium"
        case .engineLoad, .throttlePosition: "percent"
        case .controlModuleVoltage: "bolt.fill"
        }
    }
}

private struct LiveDataView: View {
    @EnvironmentObject private var connection: ConnectionManager

    var body: some View {
        NavigationStack {
            Group {
                if connection.supportedPIDs.isEmpty {
                    ContentUnavailableView(
                        connection.state == .connected ? "Waiting for PIDs" : "Not connected",
                        systemImage: "waveform.path.ecg",
                        description: Text("Live Data displays standard PIDs supported by the vehicle.")
                    )
                } else {
                    List(connection.supportedPIDs) { pid in
                        HStack {
                            VStack(alignment: .leading, spacing: 3) {
                                Text(pid.name)
                                Text(pid.command)
                                    .font(.caption.monospaced())
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            if let reading = connection.liveReadings.first(where: {
                                $0.pid.number == pid.number
                            }) {
                                Text(reading.formattedValue)
                                    .font(.body.weight(.semibold))
                                    .monospacedDigit()
                            } else {
                                Text("Supported")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            }
            .navigationTitle("Live Data")
            .toolbar { ConnectionStatusLabel() }
        }
    }
}

private struct DiagnosticsView: View {
    @EnvironmentObject private var connection: ConnectionManager
    @State private var confirmClear = false

    var body: some View {
        NavigationStack {
            List {
                if let message = connection.operationMessage {
                    Section { Text(message).foregroundStyle(.secondary) }
                }

                if connection.diagnosticCodes.isEmpty {
                    Section {
                        ContentUnavailableView(
                            "No codes loaded",
                            systemImage: "checkmark.circle",
                            description: Text("Scan to read stored, pending, and permanent trouble codes.")
                        )
                    }
                } else {
                    ForEach(["Stored", "Pending", "Permanent"], id: \.self) { category in
                        let codes = connection.diagnosticCodes.filter { $0.category == category }
                        if !codes.isEmpty {
                            Section(category) {
                                ForEach(codes) { code in
                                    Text(code.code).font(.body.monospaced().weight(.semibold))
                                }
                            }
                        }
                    }
                }

                Section {
                    Button("Scan trouble codes", systemImage: "magnifyingglass") {
                        Task { await connection.refreshDiagnosticCodes() }
                    }
                    .disabled(connection.state != .connected || connection.isBusy)

                    Button("Clear trouble codes", systemImage: "trash", role: .destructive) {
                        confirmClear = true
                    }
                    .disabled(connection.state != .connected || connection.isBusy)
                }
            }
            .navigationTitle("Diagnostics")
            .toolbar { ConnectionStatusLabel() }
            .overlay { if connection.isBusy { ProgressView().controlSize(.large) } }
            .confirmationDialog(
                "Clear diagnostic trouble codes?",
                isPresented: $confirmClear,
                titleVisibility: .visible
            ) {
                Button("Clear codes", role: .destructive) {
                    Task { await connection.clearDiagnosticCodes() }
                }
                Button("Cancel", role: .cancel) {}
            } message: {
                Text("This may also reset readiness monitors. Permanent codes are controlled by the vehicle.")
            }
        }
    }
}

private struct ReadinessView: View {
    @EnvironmentObject private var connection: ConnectionManager

    var body: some View {
        NavigationStack {
            List {
                if let message = connection.operationMessage {
                    Section { Text(message).foregroundStyle(.secondary) }
                }

                if connection.readinessResults.isEmpty {
                    Section {
                        ContentUnavailableView(
                            "No readiness results",
                            systemImage: "checklist",
                            description: Text("Refresh to read emissions monitor status.")
                        )
                    }
                } else {
                    Section("Monitors") {
                        ForEach(connection.readinessResults) { result in
                            HStack {
                                Text(result.name)
                                Spacer()
                                Label(status(for: result), systemImage: icon(for: result))
                                    .foregroundStyle(color(for: result))
                            }
                        }
                    }
                }

                Section {
                    Button("Refresh readiness", systemImage: "arrow.clockwise") {
                        Task { await connection.refreshReadiness() }
                    }
                    .disabled(connection.state != .connected || connection.isBusy)
                }
            }
            .navigationTitle("Readiness")
            .toolbar { ConnectionStatusLabel() }
            .overlay { if connection.isBusy { ProgressView().controlSize(.large) } }
        }
    }

    private func status(for result: ReadinessResult) -> String {
        !result.supported ? "Unsupported" : result.complete ? "Ready" : "Not ready"
    }

    private func icon(for result: ReadinessResult) -> String {
        !result.supported ? "minus.circle" : result.complete ? "checkmark.circle.fill" : "exclamationmark.circle.fill"
    }

    private func color(for result: ReadinessResult) -> Color {
        !result.supported ? .secondary : result.complete ? .green : .orange
    }
}

private struct ConnectionView: View {
    @EnvironmentObject private var connection: ConnectionManager

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Picker("Connection", selection: $connection.transport) {
                        ForEach(AdapterTransport.allCases) { transport in
                            Text(transport.rawValue).tag(transport)
                        }
                    }
                    .pickerStyle(.segmented)
                    .disabled(connection.state.isActive)
                }

                if connection.transport == .wifi {
                    Section("Wi-Fi adapter") {
                        TextField("IP address", text: $connection.wifiHost)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .keyboardType(.numbersAndPunctuation)
                        TextField("Port", text: $connection.wifiPort)
                            .keyboardType(.numberPad)
                    }
                } else {
                    Section("Bluetooth LE adapters") {
                        Button("Scan for adapters", systemImage: "antenna.radiowaves.left.and.right") {
                            connection.scanForBluetoothAdapters()
                        }
                        ForEach(connection.discoveredAdapters) { adapter in
                            Button {
                                connection.connect(to: adapter)
                            } label: {
                                HStack {
                                    Text(adapter.name).foregroundStyle(.primary)
                                    Spacer()
                                    Text("\(adapter.rssi) dBm")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                            }
                        }
                    }
                }

                Section {
                    HStack(spacing: 10) {
                        Circle()
                            .fill(connection.state.statusColor)
                            .frame(width: 10, height: 10)
                        Text(connection.state.title).lineLimit(2)
                        Spacer()
                    }

                    Button(connection.state.isActive ? "Disconnect" : "Connect") {
                        connection.state.isActive ? connection.disconnect() : connection.connect()
                    }
                    .buttonStyle(.borderedProminent)
                    .frame(maxWidth: .infinity)
                }
            }
            .navigationTitle("Connection")
        }
    }
}

private struct ConnectionBanner: View {
    @EnvironmentObject private var connection: ConnectionManager
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 12) {
                Circle()
                    .fill(connection.state.statusColor)
                    .frame(width: 12, height: 12)
                VStack(alignment: .leading, spacing: 2) {
                    Text(connection.state.title).font(.headline)
                    Text("Tap to configure adapter")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Image(systemName: "chevron.right").foregroundStyle(.secondary)
            }
            .mobileCard()
        }
        .buttonStyle(.plain)
    }
}

private struct ConnectionStatusLabel: ToolbarContent {
    @EnvironmentObject private var connection: ConnectionManager

    var body: some ToolbarContent {
        ToolbarItem(placement: .topBarTrailing) {
            HStack(spacing: 5) {
                Circle().fill(connection.state.statusColor).frame(width: 8, height: 8)
                Text(connection.state.title).font(.caption)
            }
        }
    }
}

private extension AdapterConnectionState {
    var statusColor: Color {
        switch self {
        case .connected: .green
        case .connecting, .reconnecting, .scanning: .orange
        case .failed: .red
        case .disconnected: .secondary
        }
    }
}

private extension View {
    func mobileCard() -> some View {
        padding(16)
            .background(
                Color(.secondarySystemGroupedBackground),
                in: RoundedRectangle(cornerRadius: 18)
            )
    }
}
