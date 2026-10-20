import Combine
@preconcurrency import CoreBluetooth
@preconcurrency import Network
import SwiftUI
import UIKit

enum AdapterTransport: String, CaseIterable, Identifiable {
    case wifi = "Wi-Fi"
    case bluetooth = "Bluetooth"

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

@MainActor
final class ConnectionManager: NSObject, ObservableObject {
    @Published var transport: AdapterTransport = .wifi
    @Published private(set) var state: AdapterConnectionState = .disconnected
    @Published var wifiHost: String
    @Published var wifiPort: String
    @Published private(set) var discoveredAdapters: [DiscoveredAdapter] = []

    private let defaults = UserDefaults.standard
    private var wifiConnection: NWConnection?
    private var centralManager: CBCentralManager!
    private var bluetoothPeripheral: CBPeripheral?
    private var bluetoothWriteCharacteristic: CBCharacteristic?
    private var reconnectTask: Task<Void, Never>?
    private var shouldReconnect = false
    private var backgroundTask = UIBackgroundTaskIdentifier.invalid

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
        centralManager.stopScan()
        wifiConnection?.cancel()
        wifiConnection = nil

        if let bluetoothPeripheral {
            centralManager.cancelPeripheralConnection(bluetoothPeripheral)
        }
        bluetoothPeripheral = nil
        bluetoothWriteCharacteristic = nil
        state = .disconnected
        endBackgroundTask()
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
            state = .connected
            receiveWiFiData()
        case .waiting:
            state = .reconnecting
        case .failed(let error):
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
        connection.receive(minimumIncompleteLength: 1, maximumLength: 65_536) { [weak self, weak connection] _, _, isComplete, error in
            Task { @MainActor in
                guard let self, let connection, connection === self.wifiConnection else { return }
                if error != nil || isComplete {
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
        }
    }

    private func scheduleReconnect() {
        guard shouldReconnect else { return }
        reconnectTask?.cancel()
        state = .reconnecting
        reconnectTask = Task { [weak self] in
            try? await Task.sleep(for: .seconds(2))
            guard !Task.isCancelled else { return }
            self?.restoreConnectionIfNeeded()
        }
    }

    private func connectBluetooth(_ peripheral: CBPeripheral) {
        centralManager.connect(
            peripheral,
            options: [CBConnectPeripheralOptionEnableAutoReconnect: true]
        )
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
        peripheral.services?.forEach { peripheral.discoverCharacteristics(nil, for: $0) }
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
            if bluetoothWriteCharacteristic == nil,
               characteristic.properties.contains(.write)
                || characteristic.properties.contains(.writeWithoutResponse) {
                bluetoothWriteCharacteristic = characteristic
                state = .connected
            }
        }
    }
}
