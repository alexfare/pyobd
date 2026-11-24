import Charts
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

            GraphsView()
                .tag(MobileSection.graphs)
                .tabItem { Label("Graphs", systemImage: "chart.xyaxis.line") }

            DiagnosticsView()
                .tag(MobileSection.diagnostics)
                .tabItem { Label("Diagnostics", systemImage: "stethoscope") }

            ReadinessView()
                .tag(MobileSection.readiness)
                .tabItem { Label("Readiness", systemImage: "checklist") }

            FreezeFrameView()
                .tag(MobileSection.freezeFrame)
                .tabItem { Label("Freeze Frame", systemImage: "snowflake") }

            VehicleProfilesView()
                .tag(MobileSection.vehicles)
                .tabItem { Label("Vehicles", systemImage: "car.2.fill") }

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

private struct GraphsView: View {
    @EnvironmentObject private var connection: ConnectionManager
    @State private var selectedPIDs: Set<StandardPID>
    @State private var showingPIDSelection = false
    @State private var isPaused = false
    @State private var pausedHistory: [StandardPID: [PIDSample]] = [:]
    @AppStorage("graphs.timeRange") private var timeRangeRaw = GraphTimeRange.thirtySeconds.rawValue

    init() {
        let defaults = UserDefaults.standard
        let stored = defaults.stringArray(forKey: "graphs.selectedPIDs") ?? []
        let selected = Set(stored.compactMap(StandardPID.init(rawValue:)))
        _selectedPIDs = State(
            initialValue: defaults.object(forKey: "graphs.selectedPIDs") == nil ? [.engineRPM] : selected
        )
    }

    private var timeRange: GraphTimeRange {
        GraphTimeRange(rawValue: timeRangeRaw) ?? .thirtySeconds
    }

    var body: some View {
        NavigationStack {
            Group {
                if selectedPIDs.isEmpty {
                    ContentUnavailableView(
                        "No graph PIDs selected",
                        systemImage: "chart.xyaxis.line",
                        description: Text("Use Select PIDs to choose values to graph.")
                    )
                } else {
                    ScrollView {
                        LazyVStack(spacing: 14) {
                            ForEach(selectedPIDs.sorted { $0.number < $1.number }) { pid in
                                GraphCard(
                                    pid: pid,
                                    samples: filteredSamples(for: pid),
                                    reading: connection.liveReadings.first { $0.pid == pid }
                                )
                            }
                        }
                        .padding()
                    }
                }
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Graphs")
            .toolbar {
                ToolbarItemGroup(placement: .topBarTrailing) {
                    Menu {
                        Button(isPaused ? "Resume" : "Pause", systemImage: isPaused ? "play.fill" : "pause.fill") {
                            togglePause()
                        }
                        Button("Clear graphs", systemImage: "trash", role: .destructive) {
                            connection.clearGraphHistory(for: selectedPIDs)
                            pausedHistory = pausedHistory.filter { !selectedPIDs.contains($0.key) }
                        }
                        Menu("Time range") {
                            Picker("Time range", selection: $timeRangeRaw) {
                                ForEach(GraphTimeRange.allCases) { range in
                                    Text(range.title).tag(range.rawValue)
                                }
                            }
                        }
                    } label: {
                        Image(systemName: "ellipsis.circle")
                    }

                    Button("Select PIDs", systemImage: "slider.horizontal.3") {
                        showingPIDSelection = true
                    }
                }
                ConnectionStatusLabel()
            }
            .sheet(isPresented: $showingPIDSelection) {
                GraphPIDSelectionView(selectedPIDs: $selectedPIDs)
            }
            .onAppear { applyGraphSelection() }
            .onChange(of: selectedPIDs) { oldValue, newValue in
                UserDefaults.standard.set(newValue.map(\.rawValue).sorted(), forKey: "graphs.selectedPIDs")
                for pid in oldValue.subtracting(newValue) {
                    connection.setGraphPIDEnabled(false, number: pid.number)
                }
                applyGraphSelection()
            }
            .onChange(of: connection.supportedPIDs) { _, _ in applyGraphSelection() }
        }
    }

    private func filteredSamples(for pid: StandardPID) -> [PIDSample] {
        let samples = isPaused ? pausedHistory[pid] ?? [] : connection.liveHistory[pid] ?? []
        guard let seconds = timeRange.seconds else { return samples }
        let end = isPaused ? samples.last?.date ?? Date() : Date()
        return samples.filter { $0.date >= end.addingTimeInterval(-seconds) }
    }

    private func applyGraphSelection() {
        for pid in selectedPIDs {
            connection.setGraphPIDEnabled(true, number: pid.number)
        }
    }

    private func togglePause() {
        if isPaused {
            pausedHistory.removeAll()
        } else {
            pausedHistory = connection.liveHistory
        }
        isPaused.toggle()
    }
}

private enum GraphTimeRange: Double, CaseIterable, Identifiable {
    case fifteenSeconds = 15
    case thirtySeconds = 30
    case oneMinute = 60
    case all = 0

    var id: Double { rawValue }
    var seconds: TimeInterval? { self == .all ? nil : rawValue }

    var title: String {
        switch self {
        case .fifteenSeconds: "15 seconds"
        case .thirtySeconds: "30 seconds"
        case .oneMinute: "1 minute"
        case .all: "All"
        }
    }
}

private struct GraphCard: View {
    let pid: StandardPID
    let samples: [PIDSample]
    let reading: PIDReading?

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                Text(pid.name).font(.headline)
                Spacer()
                Text(reading?.formattedValue ?? "—")
                    .font(.title3.bold())
                    .monospacedDigit()
            }

            if samples.isEmpty {
                ContentUnavailableView("Waiting for data", systemImage: "chart.xyaxis.line")
                    .frame(height: 150)
            } else {
                Chart(samples) { sample in
                    LineMark(
                        x: .value("Time", sample.date),
                        y: .value(pid.name, sample.value)
                    )
                    .interpolationMethod(.catmullRom)
                    .foregroundStyle(.blue)
                }
                .chartXAxis {
                    AxisMarks(values: .automatic(desiredCount: 4)) {
                        AxisGridLine()
                        AxisValueLabel(format: .dateTime.minute().second())
                    }
                }
                .frame(height: 190)
            }
        }
        .mobileCard()
    }
}

private struct GraphPIDSelectionView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var connection: ConnectionManager
    @Binding var selectedPIDs: Set<StandardPID>
    @State private var searchText = ""

    private var availablePIDs: [StandardPID] {
        let supported = connection.supportedPIDs.compactMap {
            StandardPID(rawValue: String(format: "01%02X", $0.number))
        }
        let source = supported.isEmpty
            ? StandardPID.allCases
            : Array(Set(supported).union(selectedPIDs))
        let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return source.filter {
            query.isEmpty || $0.name.lowercased().contains(query) || $0.rawValue.lowercased().contains(query)
        }
        .sorted { $0.number < $1.number }
    }

    var body: some View {
        NavigationStack {
            List(availablePIDs) { pid in
                Button {
                    if selectedPIDs.contains(pid) {
                        selectedPIDs.remove(pid)
                    } else {
                        selectedPIDs.insert(pid)
                    }
                } label: {
                    HStack {
                        VStack(alignment: .leading, spacing: 3) {
                            Text(pid.name).foregroundStyle(.primary)
                            Text(pid.rawValue).font(.caption.monospaced()).foregroundStyle(.secondary)
                        }
                        Spacer()
                        Image(systemName: selectedPIDs.contains(pid) ? "checkmark.circle.fill" : "circle")
                    }
                }
            }
            .searchable(text: $searchText, prompt: "PID or name")
            .navigationTitle("Graph PIDs")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Clear") { selectedPIDs.removeAll() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
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
                        if let profile = connection.activeVehicleProfile {
                            LabeledContent("Profile", value: profile.nickname)
                        }
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
        case .coolantTemperature, .intakeTemperature, .ambientTemperature,
             .engineOilTemperature, .catalystTemperature: "thermometer.medium"
        case .engineLoad, .throttlePosition, .fuelLevel,
             .shortFuelTrimBank1, .longFuelTrimBank1,
             .shortFuelTrimBank2, .longFuelTrimBank2: "percent"
        case .controlModuleVoltage: "bolt.fill"
        case .fuelPressure, .intakeManifoldPressure, .barometricPressure: "gauge.open.with.lines.needle.33percent"
        case .massAirFlow: "wind"
        case .timingAdvance, .fuelInjectionTiming: "clock.arrow.circlepath"
        case .engineRunTime, .distanceWithMIL, .warmupsSinceClear,
             .distanceSinceClear: "clock"
        case .engineFuelRate: "fuelpump.fill"
        }
    }
}

private struct VehicleProfilesView: View {
    @EnvironmentObject private var connection: ConnectionManager
    @State private var showingNewProfile = false

    var body: some View {
        NavigationStack {
            List {
                if connection.vehicleProfiles.isEmpty {
                    ContentUnavailableView(
                        "No vehicle profiles",
                        systemImage: "car.2",
                        description: Text("Save a vehicle to keep its Live Data selections and polling speeds.")
                    )
                } else {
                    Section("Vehicles") {
                        ForEach(connection.vehicleProfiles) { profile in
                            Button {
                                connection.selectVehicleProfile(profile.id)
                            } label: {
                                HStack {
                                    VStack(alignment: .leading, spacing: 3) {
                                        Text(profile.nickname).foregroundStyle(.primary)
                                        Text(profile.vin.isEmpty ? "No VIN saved" : profile.vin)
                                            .font(.caption.monospaced())
                                            .foregroundStyle(.secondary)
                                    }
                                    Spacer()
                                    if connection.activeVehicleProfileID == profile.id {
                                        Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
                                    }
                                }
                            }
                            .swipeActions {
                                Button("Delete", systemImage: "trash", role: .destructive) {
                                    connection.deleteVehicleProfile(profile.id)
                                }
                            }
                        }
                    }
                }

                Section {
                    Text("When a saved VIN connects, its profile and PID preferences are selected automatically.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Vehicles")
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button("Add vehicle", systemImage: "plus") {
                        showingNewProfile = true
                    }
                }
            }
            .sheet(isPresented: $showingNewProfile) {
                NewVehicleProfileView()
            }
        }
    }
}

private struct NewVehicleProfileView: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var connection: ConnectionManager
    @State private var nickname = ""
    @State private var vin = ""

    var body: some View {
        NavigationStack {
            Form {
                TextField("Vehicle nickname", text: $nickname)
                TextField("VIN", text: $vin)
                    .textInputAutocapitalization(.characters)
                    .autocorrectionDisabled()
                    .font(.body.monospaced())
            }
            .navigationTitle("New Vehicle")
            .navigationBarTitleDisplayMode(.inline)
            .onAppear {
                if connection.vehicleVIN != "—" { vin = connection.vehicleVIN }
            }
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        connection.createVehicleProfile(nickname: nickname, vin: vin)
                        dismiss()
                    }
                    .disabled(nickname.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
        }
    }
}

private struct LiveDataView: View {
    @EnvironmentObject private var connection: ConnectionManager
    @State private var showingAddPIDs = false

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
                    List {
                        if connection.isRecording {
                            Section("Recording") {
                                HStack {
                                    Label("Recording live data", systemImage: "record.circle.fill")
                                        .foregroundStyle(.red)
                                    Spacer()
                                    if let startedAt = connection.recordingStartedAt {
                                        Text(startedAt, style: .timer)
                                            .monospacedDigit()
                                    }
                                }
                                LabeledContent("Samples", value: connection.recordedSampleCount.formatted())
                            }
                        } else if let fileURL = connection.recordingFileURL {
                            Section("Last recording") {
                                ShareLink(item: fileURL) {
                                    Label("Export CSV", systemImage: "square.and.arrow.up")
                                }
                                LabeledContent("Samples", value: connection.recordedSampleCount.formatted())
                                Button("Clear recording", systemImage: "xmark.circle", role: .destructive) {
                                    connection.clearRecording()
                                }
                            }
                        }

                        if let error = connection.recordingError {
                            Section { Text(error).foregroundStyle(.red) }
                        }

                        if connection.visibleSupportedPIDs.isEmpty {
                            Section {
                                ContentUnavailableView(
                                    "No Live Data PIDs",
                                    systemImage: "waveform.path.ecg",
                                    description: Text("Use Add PIDs to choose the values shown here.")
                                )
                            }
                        }

                        ForEach(connection.visibleSupportedPIDs) { pid in
                            HStack(spacing: 12) {
                                Button {
                                    connection.toggleFavorite(pid.number)
                                } label: {
                                    Image(systemName: connection.isFavorite(pid.number) ? "star.fill" : "star")
                                        .foregroundStyle(connection.isFavorite(pid.number) ? .yellow : .secondary)
                                }
                                .buttonStyle(.plain)
                                .disabled(!connection.isDecodable(pid.number))

                                VStack(alignment: .leading, spacing: 3) {
                                    Text(pid.name)
                                    Text(pid.command)
                                        .font(.caption.monospaced())
                                        .foregroundStyle(.secondary)
                                }
                                Spacer()

                                VStack(alignment: .trailing, spacing: 3) {
                                    if let reading = connection.liveReadings.first(where: {
                                        $0.pid.number == pid.number
                                    }) {
                                        Text(reading.formattedValue)
                                            .font(.body.weight(.semibold))
                                            .monospacedDigit()
                                    } else {
                                        Text(connection.isDecodable(pid.number) ? "Not polling" : "Supported")
                                            .font(.caption)
                                            .foregroundStyle(.secondary)
                                    }
                                    if connection.isDecodable(pid.number) {
                                        Text(connection.pollingRate(for: pid.number).rawValue)
                                            .font(.caption2)
                                            .foregroundStyle(.secondary)
                                    }
                                }

                                Menu {
                                    ForEach(PIDPollingRate.allCases) { rate in
                                        Button {
                                            connection.setPollingRate(rate, for: pid.number)
                                        } label: {
                                            if connection.pollingRate(for: pid.number) == rate {
                                                Label(rate.rawValue, systemImage: "checkmark")
                                            } else {
                                                Text(rate.rawValue)
                                            }
                                        }
                                    }
                                } label: {
                                    Image(systemName: "ellipsis.circle")
                                }
                                .disabled(!connection.isDecodable(pid.number))
                            }
                            .swipeActions {
                                Button("Remove", systemImage: "trash", role: .destructive) {
                                    connection.removeLivePID(pid.number)
                                }
                            }
                        }
                    }
                }
            }
            .navigationTitle("Live Data")
            .toolbar {
                ToolbarItemGroup(placement: .topBarLeading) {
                    Button {
                        connection.isRecording
                            ? connection.stopRecording()
                            : connection.startRecording()
                    } label: {
                        Image(systemName: connection.isRecording ? "stop.circle.fill" : "record.circle")
                            .foregroundStyle(connection.isRecording ? .red : .primary)
                    }
                    .disabled(connection.state != .connected && !connection.isRecording)
                    .accessibilityLabel(connection.isRecording ? "Stop recording" : "Start recording")

                    Button {
                        showingAddPIDs = true
                    } label: {
                        Image(systemName: "plus.circle")
                    }
                    .disabled(connection.state != .connected)
                    .accessibilityLabel("Add PIDs")
                }
                ConnectionStatusLabel()
            }
            .sheet(isPresented: $showingAddPIDs) {
                AddLivePIDsView()
            }
        }
    }
}

private struct AddLivePIDsView: View {
    private enum ListMode: String, CaseIterable, Identifiable {
        case available = "Available"
        case selected = "Selected"

        var id: Self { self }
    }

    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var connection: ConnectionManager
    @State private var searchText = ""
    @State private var listMode = ListMode.available

    private var displayedPIDs: [SupportedPID] {
        switch listMode {
        case .available: connection.addableSupportedPIDs(matching: searchText)
        case .selected: connection.selectedSupportedPIDs(matching: searchText)
        }
    }

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                Picker("PID list", selection: $listMode) {
                    Text("Available").tag(ListMode.available)
                    Text("Selected (\(connection.visibleSupportedPIDs.count))").tag(ListMode.selected)
                }
                .pickerStyle(.segmented)
                .padding()

                List(displayedPIDs) { pid in
                    Button {
                        if listMode == .available {
                            connection.addLivePID(pid.number)
                        } else {
                            connection.removeLivePID(pid.number)
                        }
                    } label: {
                        HStack {
                            VStack(alignment: .leading, spacing: 3) {
                                Text(pid.name).foregroundStyle(.primary)
                                Text(pid.command)
                                    .font(.caption.monospaced())
                                    .foregroundStyle(.secondary)
                            }
                            Spacer()
                            Image(systemName: listMode == .available ? "plus.circle.fill" : "minus.circle.fill")
                                .foregroundStyle(listMode == .available ? Color.accentColor : Color.red)
                        }
                    }
                }
                .overlay {
                    if displayedPIDs.isEmpty {
                        if searchText.isEmpty {
                            ContentUnavailableView(
                                listMode == .available ? "All PIDs selected" : "No PIDs selected",
                                systemImage: listMode == .available ? "checkmark.circle" : "waveform.path.ecg"
                            )
                        } else {
                            ContentUnavailableView.search(text: searchText)
                        }
                    }
                }
            }
            .searchable(text: $searchText, prompt: "PID or name")
            .navigationTitle("Manage PIDs")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done") { dismiss() }
                }
            }
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
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(code.code)
                                            .font(.body.monospaced().weight(.semibold))
                                        Text(code.description)
                                            .font(.subheadline)
                                            .foregroundStyle(.secondary)
                                    }
                                    .padding(.vertical, 2)
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

private struct FreezeFrameView: View {
    @EnvironmentObject private var connection: ConnectionManager

    var body: some View {
        NavigationStack {
            List {
                if let message = connection.operationMessage {
                    Section { Text(message).foregroundStyle(.secondary) }
                }

                if connection.freezeFrameReadings.isEmpty {
                    Section {
                        ContentUnavailableView(
                            "No freeze-frame data",
                            systemImage: "snowflake",
                            description: Text("Load the snapshot stored when a trouble code was recorded.")
                        )
                    }
                } else {
                    Section("Frame 0") {
                        ForEach(connection.freezeFrameReadings) { reading in
                            LabeledContent(reading.pid.name, value: reading.formattedValue)
                        }
                    }
                }

                Section {
                    Button("Load freeze frame", systemImage: "arrow.clockwise") {
                        Task { await connection.refreshFreezeFrame() }
                    }
                    .disabled(connection.state != .connected || connection.isBusy)
                }
            }
            .navigationTitle("Freeze Frame")
            .toolbar { ConnectionStatusLabel() }
            .overlay { if connection.isBusy { ProgressView().controlSize(.large) } }
        }
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
                } else if connection.transport == .bluetooth {
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
                } else {
                    Section("Demo mode") {
                        Text("Explore live data, diagnostics, readiness, graphs, and freeze-frame data without an adapter.")
                            .foregroundStyle(.secondary)
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

                Section("Compatibility") {
                    Text(connection.adapterCompatibilityNote)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }

                Section("Connection diagnostics") {
                    LabeledContent("Status", value: connection.state.title)
                    LabeledContent("Target", value: connection.connectionTargetText)
                    LabeledContent("Protocol", value: connection.vehicleProtocol)
                    LabeledContent("Voltage", value: connection.adapterVoltage)
                    if let error = connection.lastConnectionError {
                        LabeledContent("Last error") {
                            Text(error).foregroundStyle(.red)
                        }
                    }
                }

                Section("About") {
                    LabeledContent("Version", value: appVersion)
                    NavigationLink("Privacy") {
                        PrivacyView()
                    }
                    Link(
                        "Support",
                        destination: URL(string: "https://farebros.com/module.php?module=app_directory&page=support&slug=pyobd")!
                    )
                }
            }
            .navigationTitle("Connection")
        }
    }

    private var appVersion: String {
        Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "—"
    }
}

private struct PrivacyView: View {
    var body: some View {
        List {
            Section("Your data") {
                Text("pyOBD Mobile does not require an account and does not send personal data, vehicle data, diagnostics, or usage analytics to Fare Brothers.")
                Text("Connection settings, vehicle profiles, PID preferences, and recordings remain on your device unless you choose to export or share them.")
            }

            Section("Adapter connections") {
                Text("The app uses Bluetooth or your local Wi-Fi network only to communicate with the vehicle adapter you select.")
            }

            Section {
                Link(
                    "View full privacy policy",
                    destination: URL(string: "https://github.com/alexfare/pyobd/blob/main/pyOBD-Mobile/PRIVACY_POLICY.md")!
                )
            }
        }
        .navigationTitle("Privacy")
        .navigationBarTitleDisplayMode(.inline)
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
