import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root
    function connectionAddress() {
        if (transport.currentText === "Wi-Fi") return wifiAddress.text
        if (transport.currentText === "USB / Serial") return serialAddress.text
        if (transport.currentText === "Bluetooth") return bluetoothAddress.text
        if (transport.currentText === "Custom URL") return customAddress.text
        return ""
    }
    clip: true
    contentWidth: availableWidth
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical.policy: ScrollBar.AsNeeded
    Component.onCompleted: {
        const saved = appModel.saved_connection()
        transport.currentIndex = Math.max(0, transport.model.indexOf(saved.transport))
        if (saved.transport === "Wi-Fi") wifiAddress.text = saved.address
        else if (saved.transport === "USB / Serial") serialAddress.text = saved.address
        else if (saved.transport === "Bluetooth") bluetoothAddress.text = saved.address
        else if (saved.transport === "Custom URL") customAddress.text = saved.address
        port.text = saved.port
        baudrate.currentIndex = Math.max(0, baudrate.model.indexOf(saved.baudrate))
        timeout.text = saved.timeout
        retries.value = Number(saved.retries)
        sendMode.currentIndex = Math.max(0, sendMode.model.indexOf(saved.send_mode))
        measurements.currentIndex = Math.max(0, measurements.model.indexOf(saved.measurement_system))
    }

    ColumnLayout {
        width: Math.min(root.availableWidth - 48, 760)
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 14
        Item { Layout.preferredHeight: 12 }
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: form.implicitHeight + 40
            radius: 16
            color: "white"
            border.color: "#dce3ec"
            ColumnLayout {
                id: form
                anchors.fill: parent
                anchors.margins: 20
                spacing: 14
                Label { text: "Adapter connection"; font.pixelSize: 20; font.bold: true; color: "#172033" }
                ComboBox {
                    id: transport
                    Layout.fillWidth: true
                    model: ["Auto detect", "Demo", "USB / Serial", "Wi-Fi", "Bluetooth", "Custom URL"]
                    onCurrentTextChanged: {
                        if (currentText === "Wi-Fi" && wifiAddress.text.trim().length === 0)
                            wifiAddress.text = "192.168.0.10"
                    }
                }
                TextField {
                    id: wifiAddress
                    Layout.fillWidth: true
                    visible: transport.currentText === "Wi-Fi"
                    placeholderText: "Adapter IP address"
                    text: "192.168.0.10"
                }
                TextField { id: serialAddress; Layout.fillWidth: true; visible: transport.currentText === "USB / Serial"; placeholderText: "COM port or serial device (blank scans automatically)" }
                TextField { id: bluetoothAddress; Layout.fillWidth: true; visible: transport.currentText === "Bluetooth"; placeholderText: "RFCOMM address or COM port" }
                TextField { id: customAddress; Layout.fillWidth: true; visible: transport.currentText === "Custom URL"; placeholderText: "Connection URL" }
                TextField { id: port; Layout.fillWidth: true; visible: transport.currentText === "Wi-Fi"; placeholderText: "Port"; text: "35000" }
                ComboBox {
                    id: baudrate
                    Layout.fillWidth: true
                    visible: transport.currentText !== "Wi-Fi" && transport.currentText !== "Demo"
                    model: ["AUTO", "38400", "9600", "115200", "57600", "19200", "14400", "3000000", "2000000", "1000000", "250000", "230400", "128000", "500000", "460800", "576000", "921600", "1152000", "1500000", "2500000", "3500000", "4000000"]
                }
                RowLayout {
                    Layout.fillWidth: true
                    visible: transport.currentText !== "Demo"
                    TextField { id: timeout; Layout.fillWidth: true; placeholderText: "Connection timeout (seconds)"; text: "2.0" }
                    Label { text: "Reconnect attempts"; color: "#64748b" }
                    SpinBox { id: retries; from: 1; to: 10; value: 3; editable: true }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: transport.currentText === "USB / Serial"
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Detected serial adapters"; font.bold: true; Layout.fillWidth: true }
                        Button { text: "Refresh"; onClicked: appModel.refresh_serial_adapters() }
                    }
                    Label { visible: appModel.serialAdapters.length === 0; text: "No serial adapters detected. Leave the port blank to scan automatically."; color: "#64748b" }
                    Repeater {
                        model: appModel.serialAdapters
                        delegate: Button {
                            required property var modelData
                            Layout.fillWidth: true
                            text: (modelData.connected ? "✓ Connected  " : "") + modelData.label
                            onClicked: serialAddress.text = modelData.target
                        }
                    }
                }
                ColumnLayout {
                    Layout.fillWidth: true
                    visible: transport.currentText === "Bluetooth"
                    RowLayout {
                        Layout.fillWidth: true
                        Label { text: "Detected Bluetooth serial adapters"; font.bold: true; Layout.fillWidth: true }
                        Button { text: "Refresh"; onClicked: appModel.refresh_bluetooth_adapters() }
                    }
                    Label {
                        visible: appModel.bluetoothAdapters.length === 0
                        text: "No connected Bluetooth serial adapters were detected."
                        color: "#64748b"
                    }
                    Repeater {
                        model: appModel.bluetoothAdapters
                        delegate: Button {
                            required property var modelData
                            Layout.fillWidth: true
                            text: (modelData.connected ? "✓ Connected  " : "") + modelData.label
                            onClicked: bluetoothAddress.text = modelData.target
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: "Send mode"; color: "#64748b" }
                    ComboBox { id: sendMode; Layout.fillWidth: true; model: ["FAST", "NORMAL"] }
                    Label { text: "Measurements"; color: "#64748b" }
                    ComboBox { id: measurements; Layout.fillWidth: true; model: ["IMPERIAL", "METRIC"] }
                }
                CheckBox { text: "Auto-connect"; enabled: false }
                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        text: "Save settings"
                        onClicked: appModel.save_connection_settings(
                            transport.currentText, root.connectionAddress(), port.text,
                            baudrate.currentText, timeout.text, retries.value.toString(),
                            sendMode.currentText, measurements.currentText
                        )
                    }
                    Button {
                        text: appModel.connected ? "Reconnect" : "Connect"
                        highlighted: true
                        onClicked: appModel.connect_vehicle(
                            transport.currentText, root.connectionAddress(), port.text,
                            baudrate.currentText, timeout.text, retries.value.toString(),
                            sendMode.currentText, measurements.currentText
                        )
                    }
                    Button { text: "Disconnect"; enabled: appModel.connectionStatus !== "Disconnected"; onClicked: appModel.disconnect_vehicle() }
                    Item { Layout.fillWidth: true }
                    Label { text: appModel.connectionStatus; font.bold: true; color: appModel.connected ? "#18864b" : "#64748b" }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Button { text: "Order OBD adapter"; onClicked: appModel.open_app_link("adapter") }
                    Item { Layout.fillWidth: true }
                    Label { text: "Changes apply on the next connection"; color: "#64748b" }
                }
                Label {
                    visible: transport.currentText === "Custom URL"
                    text: "Examples: socket://192.168.0.10:35000 or rfc2217://host:port"
                    color: "#64748b"
                }
            }
        }
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: details.implicitHeight + 40
            radius: 16
            color: "white"
            border.color: "#dce3ec"
            ColumnLayout {
                id: details
                anchors.fill: parent
                anchors.margins: 20
                Label { text: "Connection details"; font.pixelSize: 18; font.bold: true }
                Label { text: "Protocol: " + appModel.protocol; color: "#64748b" }
                Label { text: "Adapter: " + appModel.adapter; color: "#64748b" }
                Label { text: "Port: " + appModel.port; color: "#64748b"; wrapMode: Text.WrapAnywhere; Layout.fillWidth: true }
                Label { text: "VIN: " + appModel.vin; color: "#64748b" }
                Label { visible: appModel.connectionError.length > 0; text: appModel.connectionError; color: "#b91c1c"; wrapMode: Text.Wrap; Layout.fillWidth: true }
            }
        }
        Item { Layout.preferredHeight: 24 }
    }
}
