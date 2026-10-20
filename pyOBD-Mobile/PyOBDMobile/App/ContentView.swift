import SwiftUI

struct ContentView: View {
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
                        Button {
                            connection.scanForBluetoothAdapters()
                        } label: {
                            Label("Scan for adapters", systemImage: "antenna.radiowaves.left.and.right")
                        }

                        ForEach(connection.discoveredAdapters) { adapter in
                            Button {
                                connection.connect(to: adapter)
                            } label: {
                                HStack {
                                    Text(adapter.name)
                                        .foregroundStyle(.primary)
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
                            .fill(statusColor)
                            .frame(width: 10, height: 10)
                        Text(connection.state.title)
                            .lineLimit(2)
                        Spacer()
                    }

                    Button(connection.state.isActive ? "Disconnect" : "Connect") {
                        if connection.state.isActive {
                            connection.disconnect()
                        } else {
                            connection.connect()
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .frame(maxWidth: .infinity)
                }
            }
            .navigationTitle("Connection")
        }
    }

    private var statusColor: Color {
        switch connection.state {
        case .connected: .green
        case .connecting, .reconnecting, .scanning: .orange
        case .failed: .red
        case .disconnected: .secondary
        }
    }
}
