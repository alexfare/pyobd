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
    case vehicles
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

enum PIDPollingRate: String, CaseIterable, Identifiable {
    case off = "Off"
    case slow = "Slow"
    case normal = "Normal"
    case fast = "Fast"

    var id: Self { self }

    var interval: TimeInterval? {
        switch self {
        case .off: nil
        case .slow: 2
        case .normal: 0.5
        case .fast: 0.15
        }
    }
}

enum StandardPID: String, CaseIterable, Identifiable {
    case engineLoad = "0104"
    case coolantTemperature = "0105"
    case shortFuelTrimBank1 = "0106"
    case longFuelTrimBank1 = "0107"
    case shortFuelTrimBank2 = "0108"
    case longFuelTrimBank2 = "0109"
    case fuelPressure = "010A"
    case intakeManifoldPressure = "010B"
    case engineRPM = "010C"
    case vehicleSpeed = "010D"
    case timingAdvance = "010E"
    case intakeTemperature = "010F"
    case massAirFlow = "0110"
    case throttlePosition = "0111"
    case engineRunTime = "011F"
    case distanceWithMIL = "0121"
    case fuelLevel = "012F"
    case warmupsSinceClear = "0130"
    case distanceSinceClear = "0131"
    case barometricPressure = "0133"
    case catalystTemperature = "013C"
    case controlModuleVoltage = "0142"
    case ambientTemperature = "0146"
    case engineOilTemperature = "015C"
    case fuelInjectionTiming = "015D"
    case engineFuelRate = "015E"

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
        case .engineLoad, .throttlePosition, .fuelLevel:
            guard let a = bytes.first else { return nil }
            return PIDReading(pid: self, value: Double(a) * 100 / 255, unit: "%")
        case .shortFuelTrimBank1, .longFuelTrimBank1,
             .shortFuelTrimBank2, .longFuelTrimBank2:
            guard let a = bytes.first else { return nil }
            return PIDReading(pid: self, value: Double(Int(a) - 128) * 100 / 128, unit: "%")
        case .coolantTemperature, .intakeTemperature,
             .ambientTemperature, .engineOilTemperature:
            guard let a = bytes.first else { return nil }
            return PIDReading(pid: self, value: Double(Int(a) - 40), unit: "°C")
        case .fuelPressure:
            guard let a = bytes.first else { return nil }
            return PIDReading(pid: self, value: Double(a) * 3, unit: "kPa")
        case .intakeManifoldPressure, .barometricPressure:
            guard let a = bytes.first else { return nil }
            return PIDReading(pid: self, value: Double(a), unit: "kPa")
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
        case .timingAdvance:
            guard let a = bytes.first else { return nil }
            return PIDReading(pid: self, value: Double(Int(a) - 128) / 2, unit: "°")
        case .massAirFlow:
            guard bytes.count >= 2 else { return nil }
            return PIDReading(pid: self, value: Double(Self.word(bytes)) / 100, unit: "g/s")
        case .engineRunTime:
            guard bytes.count >= 2 else { return nil }
            return PIDReading(pid: self, value: Double(Self.word(bytes)), unit: "s")
        case .distanceWithMIL, .distanceSinceClear:
            guard bytes.count >= 2 else { return nil }
            return PIDReading(pid: self, value: Double(Self.word(bytes)), unit: "km")
        case .warmupsSinceClear:
            guard let a = bytes.first else { return nil }
            return PIDReading(pid: self, value: Double(a), unit: "")
        case .catalystTemperature:
            guard bytes.count >= 2 else { return nil }
            return PIDReading(pid: self, value: Double(Self.word(bytes)) / 10 - 40, unit: "°C")
        case .controlModuleVoltage:
            guard bytes.count >= 2 else { return nil }
            return PIDReading(
                pid: self,
                value: Double(Self.word(bytes)) / 1000,
                unit: "V"
            )
        case .fuelInjectionTiming:
            guard bytes.count >= 2 else { return nil }
            return PIDReading(pid: self, value: Double(Self.word(bytes) - 26_880) / 128, unit: "°")
        case .engineFuelRate:
            guard bytes.count >= 2 else { return nil }
            return PIDReading(pid: self, value: Double(Self.word(bytes)) * 0.05, unit: "L/h")
        }
    }

    private static func word(_ bytes: [UInt8]) -> Int {
        Int(bytes[0]) * 256 + Int(bytes[1])
    }
}

struct PIDReading: Identifiable, Equatable {
    let pid: StandardPID
    let value: Double
    let unit: String

    var id: String { pid.id }
    var formattedValue: String {
        switch pid {
        case .engineRPM, .vehicleSpeed, .engineRunTime,
             .distanceWithMIL, .warmupsSinceClear, .distanceSinceClear:
            "\(Int(value.rounded())) \(unit)"
                .trimmingCharacters(in: .whitespaces)
        case .coolantTemperature, .intakeTemperature,
             .ambientTemperature, .engineOilTemperature, .catalystTemperature:
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
    var description: String { DTCCatalog.description(for: code) }
}

struct ReadinessResult: Identifiable, Equatable {
    let name: String
    let supported: Bool
    let complete: Bool
    var id: String { name }
}

struct VehicleProfile: Codable, Identifiable, Equatable {
    let id: UUID
    var nickname: String
    var vin: String
    var visiblePIDNumbers: [Int]
    var favoritePIDNumbers: [Int]
    var pollingRates: [String: String]
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
    @Published private(set) var pidPollingRates: [Int: PIDPollingRate] = [:]
    @Published private(set) var favoritePIDNumbers = Set<Int>()
    @Published private(set) var visiblePIDNumbers = Set<Int>()
    @Published private(set) var diagnosticCodes: [DiagnosticCode] = []
    @Published private(set) var readinessResults: [ReadinessResult] = []
    @Published private(set) var freezeFrameReadings: [PIDReading] = []
    @Published private(set) var vehicleVIN = "—"
    @Published private(set) var vehicleProtocol = "—"
    @Published private(set) var adapterVoltage = "—"
    @Published private(set) var operationMessage: String?
    @Published private(set) var isBusy = false
    @Published private(set) var isRecording = false
    @Published private(set) var recordingStartedAt: Date?
    @Published private(set) var recordedSampleCount = 0
    @Published private(set) var recordingFileURL: URL?
    @Published private(set) var recordingError: String?
    @Published private(set) var vehicleProfiles: [VehicleProfile] = []
    @Published private(set) var activeVehicleProfileID: UUID?
    @Published private(set) var lastConnectionError: String?

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
    private var recordingHandle: FileHandle?
    private var recordingBuffer = ""
    private let recordingTimestampFormatter = ISO8601DateFormatter()
    private var pendingPIDRemovals: [Int] = []
    private var pidRemovalTask: Task<Void, Never>?

    private static let hostKey = "adapter.wifi.host"
    private static let portKey = "adapter.wifi.port"
    private static let peripheralKey = "adapter.bluetooth.peripheral"
    private static let pollingRatesKey = "liveData.pollingRates"
    private static let favoritesKey = "liveData.favorites"
    private static let visiblePIDsKey = "liveData.visiblePIDs"
    private static let vehicleProfilesKey = "vehicle.profiles"
    private static let activeVehicleProfileKey = "vehicle.activeProfile"

    override init() {
        wifiHost = UserDefaults.standard.string(forKey: Self.hostKey) ?? "192.168.0.10"
        wifiPort = UserDefaults.standard.string(forKey: Self.portKey) ?? "35000"
        super.init()
        loadPIDPreferences()
        loadVehicleProfiles()
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
        lastConnectionError = nil
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
        stopRecording()
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
        if shouldPollLiveData {
            startLivePollingIfNeeded()
        } else {
            livePollingTask?.cancel()
            livePollingTask = nil
        }
    }

    func startRecording() {
        guard state == .connected, !isRecording else { return }
        do {
            let directory = try FileManager.default.url(
                for: .documentDirectory,
                in: .userDomainMask,
                appropriateFor: nil,
                create: true
            )
            let formatter = DateFormatter()
            formatter.locale = Locale(identifier: "en_US_POSIX")
            formatter.dateFormat = "yyyyMMdd-HHmmss-SSS"
            let url = directory.appendingPathComponent(
                "pyOBD-LiveData-\(formatter.string(from: Date())).csv"
            )
            guard FileManager.default.createFile(atPath: url.path, contents: nil) else {
                throw CocoaError(.fileWriteUnknown)
            }
            let handle = try FileHandle(forWritingTo: url)
            try handle.write(contentsOf: Data("timestamp,pid,command,name,value,unit\n".utf8))
            recordingHandle = handle
            recordingBuffer = ""
            recordingFileURL = url
            recordingStartedAt = Date()
            recordedSampleCount = 0
            recordingError = nil
            isRecording = true
            startLivePollingIfNeeded()
        } catch {
            recordingError = error.localizedDescription
            recordingHandle = nil
            isRecording = false
        }
    }

    func stopRecording() {
        guard isRecording || recordingHandle != nil else { return }
        flushRecordingBuffer()
        try? recordingHandle?.close()
        recordingHandle = nil
        isRecording = false
        if !shouldPollLiveData {
            livePollingTask?.cancel()
            livePollingTask = nil
        }
    }

    func clearRecording() {
        guard !isRecording else { return }
        if let recordingFileURL {
            try? FileManager.default.removeItem(at: recordingFileURL)
        }
        recordingFileURL = nil
        recordingStartedAt = nil
        recordedSampleCount = 0
        recordingError = nil
    }

    var activeVehicleProfile: VehicleProfile? {
        vehicleProfiles.first { $0.id == activeVehicleProfileID }
    }

    var connectionTargetText: String {
        switch transport {
        case .wifi: "\(wifiHost):\(wifiPort)"
        case .bluetooth: bluetoothPeripheral?.name ?? "No BLE adapter selected"
        case .demo: "Built-in simulator"
        }
    }

    var adapterCompatibilityNote: String {
        switch transport {
        case .wifi:
            "Works with ELM327-compatible Wi-Fi adapters that expose a TCP host and port. The iPhone must remain joined to the adapter's Wi-Fi network."
        case .bluetooth:
            "Supports Bluetooth Low Energy adapters with a writable data characteristic. Generic Bluetooth Classic serial adapters are not supported by iOS."
        case .demo:
            "Uses simulated vehicle data and does not require an adapter or vehicle."
        }
    }

    func createVehicleProfile(nickname: String, vin: String) {
        let cleanName = nickname.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cleanName.isEmpty else { return }
        let profile = VehicleProfile(
            id: UUID(),
            nickname: cleanName,
            vin: Self.normalizedVIN(vin),
            visiblePIDNumbers: visiblePIDNumbers.sorted(),
            favoritePIDNumbers: favoritePIDNumbers.sorted(),
            pollingRates: Self.encodedPollingRates(pidPollingRates)
        )
        vehicleProfiles.append(profile)
        vehicleProfiles.sort { $0.nickname.localizedCaseInsensitiveCompare($1.nickname) == .orderedAscending }
        activeVehicleProfileID = profile.id
        saveVehicleProfiles()
    }

    func selectVehicleProfile(_ id: UUID) {
        guard let profile = vehicleProfiles.first(where: { $0.id == id }) else { return }
        activeVehicleProfileID = id
        applyPIDPreferences(from: profile)
        saveVehicleProfiles()
    }

    func deleteVehicleProfile(_ id: UUID) {
        vehicleProfiles.removeAll { $0.id == id }
        if activeVehicleProfileID == id {
            activeVehicleProfileID = nil
            loadPIDPreferences()
        }
        saveVehicleProfiles()
    }

    var visibleSupportedPIDs: [SupportedPID] {
        supportedPIDs.filter { visiblePIDNumbers.contains($0.number) }.sorted { lhs, rhs in
            let lhsFavorite = favoritePIDNumbers.contains(lhs.number)
            let rhsFavorite = favoritePIDNumbers.contains(rhs.number)
            if lhsFavorite != rhsFavorite { return lhsFavorite }
            return lhs.number < rhs.number
        }
    }

    func addableSupportedPIDs(matching query: String) -> [SupportedPID] {
        let normalized = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return supportedPIDs.filter { pid in
            guard isDecodable(pid.number), !visiblePIDNumbers.contains(pid.number) else { return false }
            return normalized.isEmpty
                || pid.name.lowercased().contains(normalized)
                || pid.command.lowercased().contains(normalized)
                || String(format: "%02X", pid.number).lowercased().contains(normalized)
        }
        .sorted { $0.number < $1.number }
    }

    func selectedSupportedPIDs(matching query: String) -> [SupportedPID] {
        let normalized = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        return visibleSupportedPIDs.filter { pid in
            normalized.isEmpty
                || pid.name.lowercased().contains(normalized)
                || pid.command.lowercased().contains(normalized)
                || String(format: "%02X", pid.number).lowercased().contains(normalized)
        }
    }

    func addLivePID(_ number: Int) {
        guard isDecodable(number), supportedPIDs.contains(where: { $0.number == number }) else { return }
        visiblePIDNumbers.insert(number)
        if pollingRate(for: number) == .off {
            pidPollingRates[number] = .normal
        }
        savePIDPreferences()
    }

    func removeLivePID(_ number: Int) {
        guard visiblePIDNumbers.contains(number), !pendingPIDRemovals.contains(number) else { return }
        pendingPIDRemovals.append(number)
        processPIDRemovalQueue()
    }

    func pollingRate(for number: Int) -> PIDPollingRate {
        pidPollingRates[number] ?? .off
    }

    func isFavorite(_ number: Int) -> Bool {
        favoritePIDNumbers.contains(number)
    }

    func isDecodable(_ number: Int) -> Bool {
        StandardPID(rawValue: String(format: "01%02X", number)) != nil
    }

    func setPollingRate(_ rate: PIDPollingRate, for number: Int) {
        guard isDecodable(number) else { return }
        pidPollingRates[number] = rate
        if rate == .off,
           let pid = StandardPID(rawValue: String(format: "01%02X", number)) {
            liveReadings.removeAll { $0.pid == pid }
            liveHistory[pid] = nil
        }
        savePIDPreferences()
    }

    func toggleFavorite(_ number: Int) {
        guard isDecodable(number) else { return }
        if favoritePIDNumbers.contains(number) {
            favoritePIDNumbers.remove(number)
        } else {
            favoritePIDNumbers.insert(number)
        }
        savePIDPreferences()
    }

    private func processPIDRemovalQueue() {
        guard pidRemovalTask == nil else { return }
        pidRemovalTask = Task { [weak self] in
            guard let self else { return }
            while !Task.isCancelled, let number = self.pendingPIDRemovals.first {
                try? await Task.sleep(for: .milliseconds(180))
                guard !Task.isCancelled else { break }
                self.pendingPIDRemovals.removeFirst()
                self.performLivePIDRemoval(number)
                await Task.yield()
            }
            self.pidRemovalTask = nil
        }
    }

    private func performLivePIDRemoval(_ number: Int) {
        guard visiblePIDNumbers.contains(number) else { return }
        pidPollingRates[number] = .off
        if let pid = StandardPID(rawValue: String(format: "01%02X", number)) {
            liveReadings.removeAll { $0.pid == pid }
            liveHistory[pid] = nil
        }
        favoritePIDNumbers.remove(number)
        visiblePIDNumbers.remove(number)
        savePIDPreferences()
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
            lastConnectionError = "Bluetooth is unavailable or disabled"
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
            lastConnectionError = "The Wi-Fi adapter address or port is invalid"
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
        case .waiting(let error):
            lastConnectionError = error.localizedDescription
            state = .reconnecting
        case .failed(let error):
            lastConnectionError = error.localizedDescription
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
            lastConnectionError = "Bluetooth is unavailable or disabled"
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
        stopRecording()
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
        lastConnectionError = nil
        state = .connected
        vehicleVIN = "DEMO0000000000001"
        activateProfile(matchingVIN: vehicleVIN)
        vehicleProtocol = "Demo OBD-II"
        adapterVoltage = "13.8 V"
        availablePIDs = Self.demoPIDs
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
                self.lastConnectionError = error.localizedDescription
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
                activateProfile(matchingVIN: vin)
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
              shouldPollLiveData,
              livePollingTask == nil else { return }
        livePollingTask = Task { [weak self] in
            guard let self else { return }
            var lastPollDates: [StandardPID: Date] = [:]
            while !Task.isCancelled, self.state == .connected {
                if self.transport == .demo {
                    let now = Date()
                    for reading in Self.demoReadings(at: now) {
                        guard let interval = self.pollingRate(for: reading.pid.number).interval,
                              now.timeIntervalSince(lastPollDates[reading.pid] ?? .distantPast) >= interval else {
                            continue
                        }
                        self.updateLiveReading(reading)
                        lastPollDates[reading.pid] = now
                    }
                } else {
                    let now = Date()
                    for pid in self.availablePIDs {
                        guard !Task.isCancelled else { break }
                        guard let interval = self.pollingRate(for: pid.number).interval,
                              now.timeIntervalSince(lastPollDates[pid] ?? .distantPast) >= interval else {
                            continue
                        }
                        if let response = try? await self.sendOBDCommand(pid.rawValue),
                           let reading = pid.reading(from: response) {
                            self.updateLiveReading(reading)
                        }
                        lastPollDates[pid] = Date()
                    }
                }
                try? await Task.sleep(for: .milliseconds(25))
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
        appendRecording(reading)
    }

    private var shouldPollLiveData: Bool {
        isRecording || activeSection == .overview || activeSection == .liveData || activeSection == .graphs
    }

    private func appendRecording(_ reading: PIDReading) {
        guard isRecording else { return }
        let fields = [
            recordingTimestampFormatter.string(from: Date()),
            String(format: "%02X", reading.pid.number),
            reading.pid.rawValue,
            reading.pid.name,
            String(
                format: "%.6f",
                locale: Locale(identifier: "en_US_POSIX"),
                arguments: [reading.value]
            ),
            reading.unit,
        ]
        recordingBuffer += fields.map(Self.csvField).joined(separator: ",") + "\n"
        recordedSampleCount += 1
        if recordedSampleCount.isMultiple(of: 25) {
            flushRecordingBuffer()
        }
    }

    private func flushRecordingBuffer() {
        guard !recordingBuffer.isEmpty, let recordingHandle else { return }
        do {
            try recordingHandle.write(contentsOf: Data(recordingBuffer.utf8))
            recordingBuffer = ""
        } catch {
            recordingError = error.localizedDescription
            recordingBuffer = ""
            try? recordingHandle.close()
            self.recordingHandle = nil
            isRecording = false
        }
    }

    private static func csvField(_ value: String) -> String {
        "\"\(value.replacingOccurrences(of: "\"", with: "\"\""))\""
    }

    private func loadPIDPreferences() {
        let storedRates = defaults.dictionary(forKey: Self.pollingRatesKey) as? [String: String]
        pidPollingRates = storedRates?.reduce(into: [:]) { result, entry in
            guard let number = Int(entry.key),
                  let rate = PIDPollingRate(rawValue: entry.value) else { return }
            result[number] = rate
        } ?? Dictionary(uniqueKeysWithValues: Self.defaultLivePIDs.map { ($0.number, .normal) })

        let hasStoredFavorites = defaults.object(forKey: Self.favoritesKey) != nil
        let storedFavorites = defaults.array(forKey: Self.favoritesKey) ?? []
        favoritePIDNumbers = Set(storedFavorites.compactMap {
            ($0 as? NSNumber)?.intValue
        })
        if !hasStoredFavorites {
            favoritePIDNumbers = Set([
                StandardPID.engineRPM,
                .vehicleSpeed,
                .coolantTemperature,
            ].map(\.number))
        }

        let hasStoredVisiblePIDs = defaults.object(forKey: Self.visiblePIDsKey) != nil
        let storedVisiblePIDs = defaults.array(forKey: Self.visiblePIDsKey) ?? []
        visiblePIDNumbers = Set(storedVisiblePIDs.compactMap {
            ($0 as? NSNumber)?.intValue
        })
        if !hasStoredVisiblePIDs {
            visiblePIDNumbers = Set(Self.defaultLivePIDs.map(\.number))
        }
    }

    private func savePIDPreferences() {
        if let id = activeVehicleProfileID,
           let index = vehicleProfiles.firstIndex(where: { $0.id == id }) {
            vehicleProfiles[index].visiblePIDNumbers = visiblePIDNumbers.sorted()
            vehicleProfiles[index].favoritePIDNumbers = favoritePIDNumbers.sorted()
            vehicleProfiles[index].pollingRates = Self.encodedPollingRates(pidPollingRates)
            saveVehicleProfiles()
            return
        }
        defaults.set(
            Dictionary(uniqueKeysWithValues: pidPollingRates.map {
                (String($0.key), $0.value.rawValue)
            }),
            forKey: Self.pollingRatesKey
        )
        defaults.set(favoritePIDNumbers.sorted(), forKey: Self.favoritesKey)
        defaults.set(visiblePIDNumbers.sorted(), forKey: Self.visiblePIDsKey)
    }

    private func loadVehicleProfiles() {
        if let data = defaults.data(forKey: Self.vehicleProfilesKey),
           let profiles = try? JSONDecoder().decode([VehicleProfile].self, from: data) {
            vehicleProfiles = profiles
        }
        if let rawID = defaults.string(forKey: Self.activeVehicleProfileKey),
           let id = UUID(uuidString: rawID),
           let profile = vehicleProfiles.first(where: { $0.id == id }) {
            activeVehicleProfileID = id
            applyPIDPreferences(from: profile)
        }
    }

    private func saveVehicleProfiles() {
        if let data = try? JSONEncoder().encode(vehicleProfiles) {
            defaults.set(data, forKey: Self.vehicleProfilesKey)
        }
        defaults.set(activeVehicleProfileID?.uuidString, forKey: Self.activeVehicleProfileKey)
    }

    private func applyPIDPreferences(from profile: VehicleProfile) {
        visiblePIDNumbers = Set(profile.visiblePIDNumbers)
        favoritePIDNumbers = Set(profile.favoritePIDNumbers)
        pidPollingRates = profile.pollingRates.reduce(into: [:]) { result, entry in
            guard let number = Int(entry.key),
                  let rate = PIDPollingRate(rawValue: entry.value) else { return }
            result[number] = rate
        }
    }

    private func activateProfile(matchingVIN vin: String) {
        let normalized = Self.normalizedVIN(vin)
        guard !normalized.isEmpty,
              let profile = vehicleProfiles.first(where: { Self.normalizedVIN($0.vin) == normalized }) else {
            return
        }
        activeVehicleProfileID = profile.id
        applyPIDPreferences(from: profile)
        saveVehicleProfiles()
    }

    private static func normalizedVIN(_ vin: String) -> String {
        vin.trimmingCharacters(in: .whitespacesAndNewlines).uppercased()
    }

    private static func encodedPollingRates(_ rates: [Int: PIDPollingRate]) -> [String: String] {
        Dictionary(uniqueKeysWithValues: rates.map { (String($0.key), $0.value.rawValue) })
    }

    private static func demoReadings(at date: Date) -> [PIDReading] {
        let phase = date.timeIntervalSinceReferenceDate
        return [
            PIDReading(pid: .engineLoad, value: 31 + sin(phase * 0.8) * 8, unit: "%"),
            PIDReading(pid: .coolantTemperature, value: 91 + sin(phase * 0.08) * 2, unit: "°C"),
            PIDReading(pid: .shortFuelTrimBank1, value: 1.5 + sin(phase * 0.5) * 2, unit: "%"),
            PIDReading(pid: .longFuelTrimBank1, value: 2.2, unit: "%"),
            PIDReading(pid: .shortFuelTrimBank2, value: 0.8 + sin(phase * 0.45) * 1.5, unit: "%"),
            PIDReading(pid: .longFuelTrimBank2, value: 1.7, unit: "%"),
            PIDReading(pid: .fuelPressure, value: 360 + sin(phase * 0.3) * 12, unit: "kPa"),
            PIDReading(pid: .intakeManifoldPressure, value: 42 + sin(phase * 0.7) * 5, unit: "kPa"),
            PIDReading(pid: .engineRPM, value: 820 + sin(phase * 1.4) * 90, unit: "RPM"),
            PIDReading(pid: .vehicleSpeed, value: 42 + sin(phase * 0.35) * 12, unit: "km/h"),
            PIDReading(pid: .timingAdvance, value: 12 + sin(phase * 0.5) * 3, unit: "°"),
            PIDReading(pid: .intakeTemperature, value: 28 + sin(phase * 0.1), unit: "°C"),
            PIDReading(pid: .massAirFlow, value: 7.5 + sin(phase * 0.6) * 1.2, unit: "g/s"),
            PIDReading(pid: .throttlePosition, value: 18 + sin(phase * 0.7) * 5, unit: "%"),
            PIDReading(pid: .engineRunTime, value: phase.truncatingRemainder(dividingBy: 7_200), unit: "s"),
            PIDReading(pid: .distanceWithMIL, value: 0, unit: "km"),
            PIDReading(pid: .fuelLevel, value: 64, unit: "%"),
            PIDReading(pid: .warmupsSinceClear, value: 18, unit: ""),
            PIDReading(pid: .distanceSinceClear, value: 486, unit: "km"),
            PIDReading(pid: .barometricPressure, value: 99, unit: "kPa"),
            PIDReading(pid: .catalystTemperature, value: 540 + sin(phase * 0.12) * 10, unit: "°C"),
            PIDReading(pid: .controlModuleVoltage, value: 13.8 + sin(phase * 0.2) * 0.1, unit: "V"),
            PIDReading(pid: .ambientTemperature, value: 22, unit: "°C"),
            PIDReading(pid: .engineOilTemperature, value: 96 + sin(phase * 0.08) * 2, unit: "°C"),
            PIDReading(pid: .fuelInjectionTiming, value: 4 + sin(phase * 0.3), unit: "°"),
            PIDReading(pid: .engineFuelRate, value: 2.1 + sin(phase * 0.5) * 0.3, unit: "L/h"),
        ]
    }

    private static let defaultLivePIDs: [StandardPID] = [
        .engineLoad,
        .coolantTemperature,
        .engineRPM,
        .vehicleSpeed,
        .intakeTemperature,
        .throttlePosition,
        .controlModuleVoltage,
    ]

    private static let demoPIDs = StandardPID.allCases

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
            stopRecording()
            lastConnectionError = "Bluetooth is unavailable or disabled"
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
        let message = error?.localizedDescription ?? "Bluetooth connection failed"
        lastConnectionError = message
        state = .failed(message)
        scheduleReconnect()
    }

    func centralManager(
        _ central: CBCentralManager,
        didDisconnectPeripheral peripheral: CBPeripheral,
        timestamp: CFAbsoluteTime,
        isReconnecting: Bool,
        error: Error?
    ) {
        stopRecording()
        if let error { lastConnectionError = error.localizedDescription }
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
            lastConnectionError = error.localizedDescription
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
            lastConnectionError = "No compatible Bluetooth data channel found"
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
