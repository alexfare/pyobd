import Combine
@preconcurrency import CoreBluetooth
@preconcurrency import Network
import SwiftUI
import UIKit

enum AdapterTransport: String, CaseIterable, Identifiable {
    case wifi = "Wi-Fi"
    case bluetooth = "Bluetooth"
    case demo = "Demo"

    var id: Self { self }
}

enum AdapterConnectionState: Equatable {
    case disconnected
    case scanning
    case connecting
    case connected
    case reconnecting
    case failed(String)

    var title: String {
        switch self {
        case .disconnected: "Disconnected"
        case .scanning: "Scanning"
        case .connecting: "Connecting"
        case .connected: "Connected"
        case .reconnecting: "Reconnecting"
        case .failed(let message): message
        }
    }

    var isActive: Bool {
        switch self {
        case .scanning, .connecting, .connected, .reconnecting: true
        case .disconnected, .failed: false
        }
    }
}

struct DiscoveredAdapter: Identifiable {
    let peripheral: CBPeripheral
    let name: String
    let rssi: Int

    var id: UUID { peripheral.identifier }
}

enum MobileSection: Hashable {
    case overview
    case liveData
    case graphs
    case diagnostics
    case readiness
    case freezeFrame
    case connection
}

struct SupportedPID: Identifiable, Equatable {
    let number: Int
    let name: String

    var id: Int { number }
    var command: String { String(format: "01%02X", number) }
}

enum Mode01PIDCatalog {
    static let names: [Int: String] = [
        0x01: "Status since DTCs cleared",
        0x02: "DTC that triggered the freeze frame",
        0x03: "Fuel System Status",
        0x04: "Calculated Engine Load",
        0x05: "Engine Coolant Temperature",
        0x06: "Short Term Fuel Trim - Bank 1",
        0x07: "Long Term Fuel Trim - Bank 1",
        0x08: "Short Term Fuel Trim - Bank 2",
        0x09: "Long Term Fuel Trim - Bank 2",
        0x0A: "Fuel Pressure",
        0x0B: "Intake Manifold Pressure",
        0x0C: "Engine RPM",
        0x0D: "Vehicle Speed",
        0x0E: "Timing Advance",
        0x0F: "Intake Air Temperature",
        0x10: "Air Flow Rate (MAF)",
        0x11: "Throttle Position",
        0x12: "Secondary Air Status",
        0x13: "O2 Sensors Present",
        0x14: "O2: Bank 1 - Sensor 1 Voltage",
        0x15: "O2: Bank 1 - Sensor 2 Voltage",
        0x16: "O2: Bank 1 - Sensor 3 Voltage",
        0x17: "O2: Bank 1 - Sensor 4 Voltage",
        0x18: "O2: Bank 2 - Sensor 1 Voltage",
        0x19: "O2: Bank 2 - Sensor 2 Voltage",
        0x1A: "O2: Bank 2 - Sensor 3 Voltage",
        0x1B: "O2: Bank 2 - Sensor 4 Voltage",
        0x1C: "OBD Standards Compliance",
        0x1D: "O2 Sensors Present (alternate)",
        0x1E: "Auxiliary Input Status",
        0x1F: "Engine Run Time",
        0x21: "Distance Traveled with MIL On",
        0x22: "Fuel Rail Pressure (relative to vacuum)",
        0x23: "Fuel Rail Pressure (direct injection)",
        0x24: "O2 Sensor 1 Wide-Range Lambda Voltage",
        0x25: "O2 Sensor 2 Wide-Range Lambda Voltage",
        0x26: "O2 Sensor 3 Wide-Range Lambda Voltage",
        0x27: "O2 Sensor 4 Wide-Range Lambda Voltage",
        0x28: "O2 Sensor 5 Wide-Range Lambda Voltage",
        0x29: "O2 Sensor 6 Wide-Range Lambda Voltage",
        0x2A: "O2 Sensor 7 Wide-Range Lambda Voltage",
        0x2B: "O2 Sensor 8 Wide-Range Lambda Voltage",
        0x2C: "Commanded EGR",
        0x2D: "EGR Error",
        0x2E: "Commanded Evaporative Purge",
        0x2F: "Fuel Level Input",
        0x30: "Warm-ups Since Codes Cleared",
        0x31: "Distance Traveled Since Codes Cleared",
        0x32: "Evaporative System Vapor Pressure",
        0x33: "Barometric Pressure",
        0x34: "O2 Sensor 1 Wide-Range Lambda Current",
        0x35: "O2 Sensor 2 Wide-Range Lambda Current",
        0x36: "O2 Sensor 3 Wide-Range Lambda Current",
        0x37: "O2 Sensor 4 Wide-Range Lambda Current",
        0x38: "O2 Sensor 5 Wide-Range Lambda Current",
        0x39: "O2 Sensor 6 Wide-Range Lambda Current",
        0x3A: "O2 Sensor 7 Wide-Range Lambda Current",
        0x3B: "O2 Sensor 8 Wide-Range Lambda Current",
        0x3C: "Catalyst Temperature: Bank 1 - Sensor 1",
        0x3D: "Catalyst Temperature: Bank 2 - Sensor 1",
        0x3E: "Catalyst Temperature: Bank 1 - Sensor 2",
        0x3F: "Catalyst Temperature: Bank 2 - Sensor 2",
        0x41: "Monitor Status This Drive Cycle",
        0x42: "Control Module Voltage",
        0x43: "Absolute Load Value",
        0x44: "Commanded Equivalence Ratio",
        0x45: "Relative Throttle Position",
        0x46: "Ambient Air Temperature",
        0x47: "Absolute Throttle Position B",
        0x48: "Absolute Throttle Position C",
        0x49: "Accelerator Pedal Position D",
        0x4A: "Accelerator Pedal Position E",
        0x4B: "Accelerator Pedal Position F",
        0x4C: "Commanded Throttle Actuator",
        0x4D: "Time Run with MIL On",
        0x4E: "Time Since Trouble Codes Cleared",
        0x4F: "Maximum Supported Values",
        0x50: "Maximum Mass Air Flow Rate",
        0x51: "Fuel Type",
        0x52: "Ethanol Fuel Percentage",
        0x53: "Absolute Evaporative System Vapor Pressure",
        0x54: "Evaporative System Vapor Pressure",
        0x55: "Short-Term Secondary O2 Trim - Bank 1",
        0x56: "Long-Term Secondary O2 Trim - Bank 1",
        0x57: "Short-Term Secondary O2 Trim - Bank 2",
        0x58: "Long-Term Secondary O2 Trim - Bank 2",
        0x59: "Fuel Rail Pressure (absolute)",
        0x5A: "Relative Accelerator Pedal Position",
        0x5B: "Hybrid Battery Pack Remaining Life",
        0x5C: "Engine Oil Temperature",
        0x5D: "Fuel Injection Timing",
        0x5E: "Engine Fuel Rate",
        0x5F: "Designed Emission Requirements",
    ]

    static func name(for number: Int) -> String {
        names[number] ?? String(format: "Mode 01 PID %02X", number)
    }
}

enum StandardPID: String, CaseIterable, Identifiable {
    case engineLoad = "0104"
    case coolantTemperature = "0105"
    case engineRPM = "010C"
    case vehicleSpeed = "010D"
    case intakeTemperature = "010F"
    case throttlePosition = "0111"
    case controlModuleVoltage = "0142"

    var id: String { rawValue }
    var number: Int { Int(rawValue.suffix(2), radix: 16) ?? 0 }

    var name: String {
        Mode01PIDCatalog.name(for: number)
    }

    func reading(
        from response: String,
        responseMode: UInt8 = 0x41,
        frame: UInt8? = nil
    ) -> PIDReading? {
        var marker = [responseMode, UInt8(number)]
        if let frame { marker.append(frame) }
        guard let bytes = OBDParser.payload(in: response, marker: marker) else { return nil }

        switch self {
        case .engineLoad:
            guard let a = bytes.first else { return nil }
            return PIDReading(pid: self, value: Double(a) * 100 / 255, unit: "%")
        case .coolantTemperature, .intakeTemperature:
            guard let a = bytes.first else { return nil }
            return PIDReading(pid: self, value: Double(Int(a) - 40), unit: "°C")
        case .engineRPM:
            guard bytes.count >= 2 else { return nil }
            return PIDReading(
                pid: self,
                value: Double(Int(bytes[0]) * 256 + Int(bytes[1])) / 4,
                unit: "RPM"
            )
        case .vehicleSpeed:
            guard let a = bytes.first else { return nil }
            return PIDReading(pid: self, value: Double(a), unit: "km/h")
        case .throttlePosition:
            guard let a = bytes.first else { return nil }
            return PIDReading(pid: self, value: Double(a) * 100 / 255, unit: "%")
        case .controlModuleVoltage:
            guard bytes.count >= 2 else { return nil }
            return PIDReading(
                pid: self,
                value: Double(Int(bytes[0]) * 256 + Int(bytes[1])) / 1000,
                unit: "V"
            )
        }
    }
}

struct PIDReading: Identifiable, Equatable {
    let pid: StandardPID
    let value: Double
    let unit: String

    var id: String { pid.id }
    var formattedValue: String {
        switch pid {
        case .engineRPM, .vehicleSpeed:
            "\(Int(value.rounded())) \(unit)"
        case .coolantTemperature, .intakeTemperature:
            "\(Int(value.rounded()))\(unit)"
        default:
            "\(value.formatted(.number.precision(.fractionLength(1)))) \(unit)"
        }
    }
}

struct PIDSample: Identifiable {
    let id = UUID()
    let date: Date
    let value: Double
}

struct DiagnosticCode: Identifiable, Equatable {
    let code: String
    let category: String
    var id: String { "\(category)-\(code)" }
}

struct ReadinessResult: Identifiable, Equatable {
    let name: String
    let supported: Bool
    let complete: Bool
    var id: String { name }
}

enum OBDCommandError: LocalizedError {
    case notConnected
    case timedOut
    case noData

    var errorDescription: String? {
        switch self {
        case .notConnected: "Adapter is not connected"
        case .timedOut: "Adapter did not respond"
        case .noData: "Vehicle returned no data"
        }
    }
}

enum OBDParser {
    static func bytes(in response: String) -> [UInt8] {
        response
            .uppercased()
            .components(separatedBy: CharacterSet.alphanumerics.inverted)
            .flatMap { token -> [UInt8] in
                guard !token.isEmpty,
                      token.count.isMultiple(of: 2),
                      token.allSatisfy({ $0.isHexDigit }) else { return [] }
                return stride(from: 0, to: token.count, by: 2).compactMap { offset in
                    let start = token.index(token.startIndex, offsetBy: offset)
                    let end = token.index(start, offsetBy: 2)
                    return UInt8(token[start..<end], radix: 16)
                }
            }
    }

    static func payload(in response: String, marker: [UInt8]) -> [UInt8]? {
        let data = bytes(in: response)
        guard marker.count <= data.count else { return nil }
        for index in 0...(data.count - marker.count) {
            if Array(data[index..<(index + marker.count)]) == marker {
                return Array(data.dropFirst(index + marker.count))
            }
        }
        return nil
    }

    static func troubleCodes(in response: String, responseMode: UInt8) -> [String] {
        let data = bytes(in: response)
        guard let modeIndex = data.firstIndex(of: responseMode) else { return [] }
        let payload = Array(data.dropFirst(modeIndex + 1))
        var codes: [String] = []
        for index in stride(from: 0, to: payload.count - 1, by: 2) {
            let first = payload[index]
            let second = payload[index + 1]
            guard first != 0 || second != 0 else { continue }
            let family = ["P", "C", "B", "U"][Int(first >> 6)]
            let code = String(
                format: "%@%01X%02X",
                family,
                Int((first >> 4) & 0x03),
                Int(first & 0x0F) * 256 + Int(second)
            )
            codes.append(code)
        }
        return codes
    }
}

@MainActor
final class ConnectionManager: NSObject, ObservableObject {
    @Published var transport: AdapterTransport = .wifi
    @Published private(set) var state: AdapterConnectionState = .disconnected
    @Published var wifiHost: String
    @Published var wifiPort: String
    @Published private(set) var discoveredAdapters: [DiscoveredAdapter] = []
    @Published private(set) var supportedPIDs: [SupportedPID] = []
    @Published private(set) var liveReadings: [PIDReading] = []
    @Published private(set) var liveHistory: [StandardPID: [PIDSample]] = [:]
    @Published private(set) var diagnosticCodes: [DiagnosticCode] = []
    @Published private(set) var readinessResults: [ReadinessResult] = []
    @Published private(set) var freezeFrameReadings: [PIDReading] = []
    @Published private(set) var vehicleVIN = "—"
    @Published private(set) var vehicleProtocol = "—"
    @Published private(set) var adapterVoltage = "—"
    @Published private(set) var operationMessage: String?
    @Published private(set) var isBusy = false

    private struct QueuedCommand {
        let id: UUID
        let text: String
        let continuation: CheckedContinuation<String, Error>
    }

    private let defaults = UserDefaults.standard
    private var wifiConnection: NWConnection?
    private var centralManager: CBCentralManager!
    private var bluetoothPeripheral: CBPeripheral?
    private var bluetoothWriteCharacteristic: CBCharacteristic?
    private var bluetoothWriteCandidates: [CBCharacteristic] = []
    private var pendingBluetoothServices = Set<CBUUID>()
    private var reconnectTask: Task<Void, Never>?
    private var initializationTask: Task<Void, Never>?
    private var livePollingTask: Task<Void, Never>?
    private var shouldReconnect = false
    private var backgroundTask = UIBackgroundTaskIdentifier.invalid
    private var commandQueue: [QueuedCommand] = []
    private var activeCommand: QueuedCommand?
    private var responseBuffer = ""
    private var availablePIDs = StandardPID.allCases
    private var activeSection: MobileSection = .connection

    private static let hostKey = "adapter.wifi.host"
    private static let portKey = "adapter.wifi.port"
    private static let peripheralKey = "adapter.bluetooth.peripheral"

    override init() {
        wifiHost = UserDefaults.standard.string(forKey: Self.hostKey) ?? "192.168.0.10"
        wifiPort = UserDefaults.standard.string(forKey: Self.portKey) ?? "35000"
        super.init()
        let backgroundModes = Bundle.main.object(forInfoDictionaryKey: "UIBackgroundModes") as? [String]
        let options: [String: Any]? = backgroundModes?.contains("bluetooth-central") == true
            ? [CBCentralManagerOptionRestoreIdentifierKey: "com.farebros.pyobd.bluetooth"]
            : nil
        centralManager = CBCentralManager(
            delegate: self,
            queue: .main,
            options: options
        )
    }

    func connect() {
        shouldReconnect = true
        reconnectTask?.cancel()

        switch transport {
        case .wifi:
            connectWiFi()
        case .bluetooth:
            reconnectBluetoothOrScan()
        case .demo:
            connectDemo()
        }
    }

    func connect(to adapter: DiscoveredAdapter) {
        shouldReconnect = true
        centralManager.stopScan()
        bluetoothPeripheral = adapter.peripheral
        defaults.set(adapter.id.uuidString, forKey: Self.peripheralKey)
        state = .connecting
        connectBluetooth(adapter.peripheral)
    }

    func disconnect() {
        shouldReconnect = false
        reconnectTask?.cancel()
        reconnectTask = nil
        initializationTask?.cancel()
        initializationTask = nil
        livePollingTask?.cancel()
        livePollingTask = nil
        failPendingCommands(with: OBDCommandError.notConnected)
        centralManager.stopScan()
        wifiConnection?.cancel()
        wifiConnection = nil

        if let bluetoothPeripheral {
            centralManager.cancelPeripheralConnection(bluetoothPeripheral)
        }
        bluetoothPeripheral = nil
        bluetoothWriteCharacteristic = nil
        bluetoothWriteCandidates.removeAll()
        pendingBluetoothServices.removeAll()
        supportedPIDs.removeAll()
        liveReadings.removeAll()
        liveHistory.removeAll()
        diagnosticCodes.removeAll()
        readinessResults.removeAll()
        freezeFrameReadings.removeAll()
        vehicleVIN = "—"
        vehicleProtocol = "—"
        adapterVoltage = "—"
        operationMessage = nil
        state = .disconnected
        endBackgroundTask()
    }

    func setActiveSection(_ section: MobileSection) {
        activeSection = section
        if section == .overview || section == .liveData || section == .graphs {
            startLivePollingIfNeeded()
        } else {
            livePollingTask?.cancel()
            livePollingTask = nil
        }
    }

    func refreshDiagnosticCodes() async {
        guard state == .connected else { return }
        if transport == .demo {
            diagnosticCodes = [
                DiagnosticCode(code: "P0300", category: "Stored"),
                DiagnosticCode(code: "P0456", category: "Pending"),
            ]
            operationMessage = nil
            return
        }
        isBusy = true
        operationMessage = nil
        defer { isBusy = false }

        do {
            let categories: [(String, String, UInt8)] = [
                ("Stored", "03", 0x43),
                ("Pending", "07", 0x47),
                ("Permanent", "0A", 0x4A),
            ]
            var results: [DiagnosticCode] = []
            for (category, command, responseMode) in categories {
                let response = try await sendOBDCommand(command)
                results.append(contentsOf: OBDParser.troubleCodes(
                    in: response,
                    responseMode: responseMode
                ).map { DiagnosticCode(code: $0, category: category) })
            }
            diagnosticCodes = results
            operationMessage = results.isEmpty ? "No diagnostic trouble codes found" : nil
        } catch {
            operationMessage = error.localizedDescription
        }
    }

    func clearDiagnosticCodes() async {
        guard state == .connected else { return }
        if transport == .demo {
            diagnosticCodes.removeAll()
            operationMessage = "Demo codes cleared"
            return
        }
        isBusy = true
        operationMessage = nil
        defer { isBusy = false }
        do {
            _ = try await sendOBDCommand("04")
            diagnosticCodes.removeAll()
            operationMessage = "Clear-code command sent"
        } catch {
            operationMessage = error.localizedDescription
        }
    }

    func refreshReadiness() async {
        guard state == .connected else { return }
        if transport == .demo {
            readinessResults = Self.demoReadiness
            operationMessage = nil
            return
        }
        isBusy = true
        operationMessage = nil
        defer { isBusy = false }
        do {
            let response = try await sendOBDCommand("0101")
            guard let bytes = OBDParser.payload(in: response, marker: [0x41, 0x01]),
                  bytes.count >= 4 else { throw OBDCommandError.noData }
            readinessResults = Self.decodeReadiness(bytes: bytes)
        } catch {
            operationMessage = error.localizedDescription
        }
    }

    func refreshFreezeFrame() async {
        guard state == .connected else { return }
        if transport == .demo {
            freezeFrameReadings = Self.demoReadings(at: Date()).map {
                PIDReading(pid: $0.pid, value: $0.value * 0.92, unit: $0.unit)
            }
            operationMessage = nil
            return
        }

        isBusy = true
        operationMessage = nil
        defer { isBusy = false }
        var readings: [PIDReading] = []
        for pid in availablePIDs {
            do {
                let command = String(format: "02%02X00", pid.number)
                let response = try await sendOBDCommand(command)
                if let reading = pid.reading(from: response, responseMode: 0x42, frame: 0x00) {
                    readings.append(reading)
                }
            } catch {
                continue
            }
        }
        freezeFrameReadings = readings
        if readings.isEmpty { operationMessage = "No freeze-frame data available" }
    }

    func scanForBluetoothAdapters() {
        transport = .bluetooth
        guard centralManager.state == .poweredOn else {
            state = .failed("Bluetooth unavailable")
            return
        }

        discoveredAdapters.removeAll()
        state = .scanning
        centralManager.scanForPeripherals(
            withServices: nil,
            options: [CBCentralManagerScanOptionAllowDuplicatesKey: false]
        )
    }

    func scenePhaseChanged(_ phase: ScenePhase) {
        switch phase {
        case .background:
            beginBackgroundTask()
        case .active:
            endBackgroundTask()
            restoreConnectionIfNeeded()
        case .inactive:
            break
        @unknown default:
            break
        }
    }

    private func connectWiFi() {
        guard let rawPort = UInt16(wifiPort),
              let port = NWEndpoint.Port(rawValue: rawPort),
              !wifiHost.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            state = .failed("Check Wi-Fi address")
            return
        }

        defaults.set(wifiHost, forKey: Self.hostKey)
        defaults.set(wifiPort, forKey: Self.portKey)
        wifiConnection?.cancel()

        let tcp = NWProtocolTCP.Options()
        tcp.enableKeepalive = true
        tcp.keepaliveIdle = 10
        tcp.keepaliveInterval = 5
        tcp.keepaliveCount = 3

        let parameters = NWParameters(tls: nil, tcp: tcp)
        parameters.serviceClass = .responsiveData
        let connection = NWConnection(host: NWEndpoint.Host(wifiHost), port: port, using: parameters)
        wifiConnection = connection
        state = state == .reconnecting ? .reconnecting : .connecting

        connection.stateUpdateHandler = { [weak self, weak connection] newState in
            Task { @MainActor in
                guard let self, let connection, connection === self.wifiConnection else { return }
                self.handleWiFiState(newState)
            }
        }
        connection.start(queue: .global(qos: .userInitiated))
    }

    private func handleWiFiState(_ newState: NWConnection.State) {
        switch newState {
        case .ready:
            receiveWiFiData()
            beginAdapterInitialization()
        case .waiting:
            state = .reconnecting
        case .failed(let error):
            failPendingCommands(with: error)
            state = .failed(error.localizedDescription)
            scheduleReconnect()
        case .cancelled:
            if shouldReconnect { scheduleReconnect() }
        default:
            break
        }
    }

    private func receiveWiFiData() {
        guard let connection = wifiConnection else { return }
        connection.receive(minimumIncompleteLength: 1, maximumLength: 65_536) { [weak self, weak connection] data, _, isComplete, error in
            Task { @MainActor in
                guard let self, let connection, connection === self.wifiConnection else { return }
                if let data {
                    self.consumeAdapterData(data)
                }
                if error != nil || isComplete {
                    self.failPendingCommands(with: OBDCommandError.notConnected)
                    self.state = .reconnecting
                    self.scheduleReconnect()
                } else {
                    self.receiveWiFiData()
                }
            }
        }
    }

    private func reconnectBluetoothOrScan() {
        guard centralManager.state == .poweredOn else {
            state = .failed("Bluetooth unavailable")
            return
        }

        if let rawID = defaults.string(forKey: Self.peripheralKey),
           let id = UUID(uuidString: rawID),
           let peripheral = centralManager.retrievePeripherals(withIdentifiers: [id]).first {
            bluetoothPeripheral = peripheral
            state = .connecting
            connectBluetooth(peripheral)
        } else {
            scanForBluetoothAdapters()
        }
    }

    private func restoreConnectionIfNeeded() {
        guard shouldReconnect, state != .connected, state != .connecting else { return }
        state = .reconnecting
        switch transport {
        case .wifi: connectWiFi()
        case .bluetooth: reconnectBluetoothOrScan()
        case .demo: connectDemo()
        }
    }

    private func scheduleReconnect() {
        guard shouldReconnect else { return }
        reconnectTask?.cancel()
        initializationTask?.cancel()
        livePollingTask?.cancel()
        livePollingTask = nil
        state = .reconnecting
        reconnectTask = Task { [weak self] in
            try? await Task.sleep(for: .seconds(2))
            guard !Task.isCancelled else { return }
            self?.restoreConnectionIfNeeded()
        }
    }

    private func connectBluetooth(_ peripheral: CBPeripheral) {
        bluetoothWriteCharacteristic = nil
        bluetoothWriteCandidates.removeAll()
        pendingBluetoothServices.removeAll()
        centralManager.connect(
            peripheral,
            options: [CBConnectPeripheralOptionEnableAutoReconnect: true]
        )
    }

    private func connectDemo() {
        shouldReconnect = false
        state = .connected
        vehicleVIN = "DEMO0000000000001"
        vehicleProtocol = "Demo OBD-II"
        adapterVoltage = "13.8 V"
        availablePIDs = StandardPID.allCases
        supportedPIDs = availablePIDs.map { SupportedPID(number: $0.number, name: $0.name) }
        readinessResults = Self.demoReadiness
        startLivePollingIfNeeded()
    }

    private func beginBackgroundTask() {
        guard backgroundTask == .invalid else { return }
        backgroundTask = UIApplication.shared.beginBackgroundTask(withName: "Maintain adapter connection") { [weak self] in
            Task { @MainActor in self?.endBackgroundTask() }
        }
    }

    private func endBackgroundTask() {
        guard backgroundTask != .invalid else { return }
        UIApplication.shared.endBackgroundTask(backgroundTask)
        backgroundTask = .invalid
    }

    private func beginAdapterInitialization() {
        initializationTask?.cancel()
        operationMessage = nil
        state = .connecting
        initializationTask = Task { [weak self] in
            guard let self else { return }
            do {
                for command in ["ATZ", "ATE0", "ATL0", "ATS0", "ATH0", "ATSP0"] {
                    _ = try await self.sendOBDCommand(command)
                }
                try Task.checkCancellation()
                self.state = .connected
                await self.loadVehicleSummary()
                await self.loadSupportedPIDs()
                self.startLivePollingIfNeeded()
            } catch is CancellationError {
                return
            } catch {
                guard self.shouldReconnect, !Task.isCancelled else { return }
                self.state = .failed(error.localizedDescription)
                self.scheduleReconnect()
            }
        }
    }

    private func sendOBDCommand(_ command: String) async throws -> String {
        guard wifiConnection != nil || bluetoothWriteCharacteristic != nil else {
            throw OBDCommandError.notConnected
        }
        return try await withCheckedThrowingContinuation { continuation in
            commandQueue.append(QueuedCommand(
                id: UUID(),
                text: command.uppercased(),
                continuation: continuation
            ))
            sendNextCommandIfNeeded()
        }
    }

    private func sendNextCommandIfNeeded() {
        guard activeCommand == nil, !commandQueue.isEmpty else { return }
        let command = commandQueue.removeFirst()
        activeCommand = command
        responseBuffer = ""
        let data = Data("\(command.text)\r".utf8)

        if transport == .wifi, let wifiConnection {
            wifiConnection.send(content: data, completion: .contentProcessed { _ in })
        } else if let bluetoothPeripheral, let bluetoothWriteCharacteristic {
            let writeType: CBCharacteristicWriteType = bluetoothWriteCharacteristic.properties
                .contains(.writeWithoutResponse) ? .withoutResponse : .withResponse
            bluetoothPeripheral.writeValue(data, for: bluetoothWriteCharacteristic, type: writeType)
        } else {
            activeCommand = nil
            command.continuation.resume(throwing: OBDCommandError.notConnected)
            sendNextCommandIfNeeded()
            return
        }

        Task { [weak self] in
            try? await Task.sleep(for: .seconds(5))
            self?.timeoutCommand(command.id)
        }
    }

    private func timeoutCommand(_ id: UUID) {
        guard activeCommand?.id == id else { return }
        let command = activeCommand
        activeCommand = nil
        responseBuffer = ""
        command?.continuation.resume(throwing: OBDCommandError.timedOut)
        sendNextCommandIfNeeded()
    }

    private func consumeAdapterData(_ data: Data) {
        guard let text = String(data: data, encoding: .utf8) else { return }
        responseBuffer += text.replacingOccurrences(of: "\0", with: "")
        while let prompt = responseBuffer.firstIndex(of: ">") {
            let response = String(responseBuffer[..<prompt])
            responseBuffer = String(responseBuffer[responseBuffer.index(after: prompt)...])
            guard let command = activeCommand else { continue }
            activeCommand = nil
            command.continuation.resume(returning: response)
            sendNextCommandIfNeeded()
        }
    }

    private func failPendingCommands(with error: Error) {
        initializationTask?.cancel()
        if let activeCommand {
            activeCommand.continuation.resume(throwing: error)
        }
        activeCommand = nil
        commandQueue.forEach { $0.continuation.resume(throwing: error) }
        commandQueue.removeAll()
        responseBuffer = ""
    }

    private func loadVehicleSummary() async {
        do {
            vehicleProtocol = Self.cleanTextResponse(try await sendOBDCommand("ATDP"))
            adapterVoltage = Self.cleanTextResponse(try await sendOBDCommand("ATRV"))
            let vinResponse = try await sendOBDCommand("0902")
            if let vin = Self.decodeVIN(vinResponse), !vin.isEmpty {
                vehicleVIN = vin
            }
        } catch {
            operationMessage = "Connected; some vehicle details are unavailable"
        }
    }

    private func loadSupportedPIDs() async {
        var supportedNumbers = Set<Int>()
        do {
            for base in [0x00, 0x20, 0x40] {
                let command = String(format: "01%02X", base)
                let response = try await sendOBDCommand(command)
                guard let bytes = OBDParser.payload(
                    in: response,
                    marker: [0x41, UInt8(base)]
                ), bytes.count >= 4 else { continue }
                let mask = bytes.prefix(4).reduce(UInt32(0)) { ($0 << 8) | UInt32($1) }
                for offset in 1...32 where mask & (UInt32(1) << UInt32(32 - offset)) != 0 {
                    supportedNumbers.insert(base + offset)
                }
            }
            supportedPIDs = supportedNumbers
                .filter { $0 != 0x20 && $0 != 0x40 && $0 != 0x60 }
                .sorted()
                .map { SupportedPID(
                    number: $0,
                    name: Mode01PIDCatalog.name(for: $0)
                ) }
            let supported = StandardPID.allCases.filter { supportedNumbers.contains($0.number) }
            if !supported.isEmpty { availablePIDs = supported }
        } catch {
            supportedPIDs = StandardPID.allCases.map {
                SupportedPID(number: $0.number, name: $0.name)
            }
            availablePIDs = StandardPID.allCases
        }
    }

    private func startLivePollingIfNeeded() {
        guard state == .connected,
              activeSection == .overview || activeSection == .liveData,
              livePollingTask == nil else { return }
        livePollingTask = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled, self.state == .connected {
                if self.transport == .demo {
                    for reading in Self.demoReadings(at: Date()) {
                        self.updateLiveReading(reading)
                    }
                    try? await Task.sleep(for: .milliseconds(250))
                } else {
                    for pid in self.availablePIDs {
                        guard !Task.isCancelled else { break }
                        if let response = try? await self.sendOBDCommand(pid.rawValue),
                           let reading = pid.reading(from: response) {
                            self.updateLiveReading(reading)
                        }
                    }
                    try? await Task.sleep(for: .milliseconds(50))
                }
            }
            self.livePollingTask = nil
        }
    }

    private func updateLiveReading(_ reading: PIDReading) {
        if let index = liveReadings.firstIndex(where: { $0.pid == reading.pid }) {
            liveReadings[index] = reading
        } else {
            liveReadings.append(reading)
            liveReadings.sort { $0.pid.number < $1.pid.number }
        }
        var samples = liveHistory[reading.pid, default: []]
        samples.append(PIDSample(date: Date(), value: reading.value))
        if samples.count > 180 { samples.removeFirst(samples.count - 180) }
        liveHistory[reading.pid] = samples
    }

    private static func demoReadings(at date: Date) -> [PIDReading] {
        let phase = date.timeIntervalSinceReferenceDate
        return [
            PIDReading(pid: .engineLoad, value: 31 + sin(phase * 0.8) * 8, unit: "%"),
            PIDReading(pid: .coolantTemperature, value: 91 + sin(phase * 0.08) * 2, unit: "°C"),
            PIDReading(pid: .engineRPM, value: 820 + sin(phase * 1.4) * 90, unit: "RPM"),
            PIDReading(pid: .vehicleSpeed, value: 42 + sin(phase * 0.35) * 12, unit: "km/h"),
            PIDReading(pid: .intakeTemperature, value: 28 + sin(phase * 0.1), unit: "°C"),
            PIDReading(pid: .throttlePosition, value: 18 + sin(phase * 0.7) * 5, unit: "%"),
            PIDReading(pid: .controlModuleVoltage, value: 13.8 + sin(phase * 0.2) * 0.1, unit: "V"),
        ]
    }

    private static let demoReadiness = [
        ReadinessResult(name: "Misfire", supported: true, complete: true),
        ReadinessResult(name: "Fuel system", supported: true, complete: true),
        ReadinessResult(name: "Components", supported: true, complete: true),
        ReadinessResult(name: "Catalyst", supported: true, complete: true),
        ReadinessResult(name: "Evaporative system", supported: true, complete: false),
        ReadinessResult(name: "Oxygen sensor", supported: true, complete: true),
    ]

    private static func cleanTextResponse(_ response: String) -> String {
        response
            .components(separatedBy: .newlines)
            .map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
            .first { !$0.isEmpty && $0 != ">" } ?? "—"
    }

    private static func decodeVIN(_ response: String) -> String? {
        guard let payload = OBDParser.payload(in: response, marker: [0x49, 0x02]) else {
            return nil
        }
        let vinBytes = payload.filter { $0 >= 0x20 && $0 <= 0x7E }
        return String(bytes: vinBytes, encoding: .ascii)?.trimmingCharacters(in: .whitespaces)
    }

    private static func decodeReadiness(bytes: [UInt8]) -> [ReadinessResult] {
        let b = bytes[1]
        let c = bytes[2]
        let d = bytes[3]
        var results = [
            readinessResult("Misfire", supported: b & 0x01 != 0, incomplete: b & 0x10 != 0),
            readinessResult("Fuel system", supported: b & 0x02 != 0, incomplete: b & 0x20 != 0),
            readinessResult("Components", supported: b & 0x04 != 0, incomplete: b & 0x40 != 0),
        ]
        let names = b & 0x08 == 0
            ? [
                "Catalyst", "Heated catalyst", "Evaporative system", "Secondary air",
                "A/C refrigerant", "Oxygen sensor", "Oxygen sensor heater", "EGR/VVT",
            ]
            : [
                "NMHC catalyst", "NOx/SCR", "Reserved", "Boost pressure",
                "Reserved", "Exhaust gas sensor", "PM filter", "EGR/VVT",
            ]
        for bit in 0..<8 {
            let mask = UInt8(1 << bit)
            results.append(readinessResult(
                names[bit],
                supported: c & mask != 0,
                incomplete: d & mask != 0
            ))
        }
        return results
    }

    private static func readinessResult(
        _ name: String,
        supported: Bool,
        incomplete: Bool
    ) -> ReadinessResult {
        ReadinessResult(name: name, supported: supported, complete: supported && !incomplete)
    }
}

extension ConnectionManager: @preconcurrency CBCentralManagerDelegate {
    func centralManagerDidUpdateState(_ central: CBCentralManager) {
        if central.state == .poweredOn, shouldReconnect, transport == .bluetooth {
            reconnectBluetoothOrScan()
        } else if central.state != .poweredOn, transport == .bluetooth {
            state = .failed("Bluetooth unavailable")
        }
    }

    func centralManager(
        _ central: CBCentralManager,
        willRestoreState dict: [String: Any]
    ) {
        guard let peripherals = dict[CBCentralManagerRestoredStatePeripheralsKey] as? [CBPeripheral],
              let peripheral = peripherals.first else { return }
        transport = .bluetooth
        shouldReconnect = true
        bluetoothPeripheral = peripheral
        peripheral.delegate = self
        state = peripheral.state == .connected ? .connecting : .reconnecting
        if peripheral.state == .connected {
            peripheral.discoverServices(nil)
        } else {
            connectBluetooth(peripheral)
        }
    }

    func centralManager(
        _ central: CBCentralManager,
        didDiscover peripheral: CBPeripheral,
        advertisementData: [String: Any],
        rssi RSSI: NSNumber
    ) {
        let name = peripheral.name
            ?? advertisementData[CBAdvertisementDataLocalNameKey] as? String
            ?? "Bluetooth adapter"
        let adapter = DiscoveredAdapter(peripheral: peripheral, name: name, rssi: RSSI.intValue)
        if let index = discoveredAdapters.firstIndex(where: { $0.id == adapter.id }) {
            discoveredAdapters[index] = adapter
        } else {
            discoveredAdapters.append(adapter)
            discoveredAdapters.sort { $0.rssi > $1.rssi }
        }
    }

    func centralManager(_ central: CBCentralManager, didConnect peripheral: CBPeripheral) {
        bluetoothPeripheral = peripheral
        bluetoothWriteCharacteristic = nil
        bluetoothWriteCandidates.removeAll()
        pendingBluetoothServices.removeAll()
        peripheral.delegate = self
        peripheral.discoverServices(nil)
    }

    func centralManager(
        _ central: CBCentralManager,
        didFailToConnect peripheral: CBPeripheral,
        error: Error?
    ) {
        state = .failed(error?.localizedDescription ?? "Bluetooth connection failed")
        scheduleReconnect()
    }

    func centralManager(
        _ central: CBCentralManager,
        didDisconnectPeripheral peripheral: CBPeripheral,
        timestamp: CFAbsoluteTime,
        isReconnecting: Bool,
        error: Error?
    ) {
        bluetoothWriteCharacteristic = nil
        failPendingCommands(with: error ?? OBDCommandError.notConnected)
        if shouldReconnect {
            state = .reconnecting
            if !isReconnecting {
                connectBluetooth(peripheral)
            }
        } else {
            state = .disconnected
        }
    }
}

extension ConnectionManager: @preconcurrency CBPeripheralDelegate {
    func peripheral(_ peripheral: CBPeripheral, didDiscoverServices error: Error?) {
        if let error {
            state = .failed(error.localizedDescription)
            scheduleReconnect()
            return
        }
        let services = peripheral.services ?? []
        pendingBluetoothServices = Set(services.map(\.uuid))
        services.forEach { peripheral.discoverCharacteristics(nil, for: $0) }
    }

    func peripheral(
        _ peripheral: CBPeripheral,
        didDiscoverCharacteristicsFor service: CBService,
        error: Error?
    ) {
        guard error == nil else { return }
        for characteristic in service.characteristics ?? [] {
            if characteristic.properties.contains(.notify) || characteristic.properties.contains(.indicate) {
                peripheral.setNotifyValue(true, for: characteristic)
            }
            if characteristic.properties.contains(.write)
                || characteristic.properties.contains(.writeWithoutResponse) {
                bluetoothWriteCandidates.append(characteristic)
            }
        }
        pendingBluetoothServices.remove(service.uuid)
        guard pendingBluetoothServices.isEmpty, bluetoothWriteCharacteristic == nil else { return }
        bluetoothWriteCharacteristic = bluetoothWriteCandidates.max {
            Self.bluetoothWritePriority($0) < Self.bluetoothWritePriority($1)
        }
        guard bluetoothWriteCharacteristic != nil else {
            state = .failed("No compatible Bluetooth data channel found")
            return
        }
        Task { [weak self] in
            try? await Task.sleep(for: .milliseconds(250))
            guard !Task.isCancelled else { return }
            self?.beginAdapterInitialization()
        }
    }

    func peripheral(
        _ peripheral: CBPeripheral,
        didUpdateValueFor characteristic: CBCharacteristic,
        error: Error?
    ) {
        guard error == nil, let data = characteristic.value else { return }
        consumeAdapterData(data)
    }
}

private extension ConnectionManager {
    static func bluetoothWritePriority(_ characteristic: CBCharacteristic) -> Int {
        switch characteristic.uuid.uuidString.uppercased() {
        case "6E400002-B5A3-F393-E0A9-E50E24DCCA9E": 100
        case "FFE1", "FFF2", "ABF1": 90
        default: characteristic.properties.contains(.writeWithoutResponse) ? 20 : 10
        }
    }
}
