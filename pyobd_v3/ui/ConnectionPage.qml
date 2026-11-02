import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root
    clip: true
    contentWidth: availableWidth
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical.policy: ScrollBar.AsNeeded
    Component.onCompleted: {
        const saved = appModel.saved_connection()
        transport.currentIndex = Math.max(0, transport.model.indexOf(saved.transport))
        address.text = saved.address
        port.text = saved.port
        baudrate.currentIndex = Math.max(0, baudrate.model.indexOf(saved.baudrate))
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
                    model: ["Wi-Fi", "USB / Serial", "Bluetooth", "Custom URL", "Demo"]
                    onCurrentTextChanged: {
                        if (currentText === "Wi-Fi" && address.text.trim().length === 0)
                            address.text = "192.168.0.10"
                    }
                }
                TextField {
                    id: address
                    Layout.fillWidth: true
                    visible: transport.currentText !== "Demo"
                    placeholderText: transport.currentText === "Wi-Fi" ? "Adapter IP address" : transport.currentText === "Bluetooth" ? "RFCOMM address or COM port" : "Serial port or connection URL"
                }
                TextField { id: port; Layout.fillWidth: true; visible: transport.currentText === "Wi-Fi"; placeholderText: "Port"; text: "35000" }
                ComboBox { id: baudrate; Layout.fillWidth: true; visible: transport.currentText !== "Wi-Fi" && transport.currentText !== "Demo"; model: ["AUTO", "38400", "9600", "115200"] }
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
                            onClicked: address.text = modelData.target
                        }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        text: appModel.connected ? "Reconnect" : "Connect"
                        highlighted: true
                        onClicked: appModel.connect_vehicle(transport.currentText, address.text, port.text, baudrate.currentText)
                    }
                    Button { text: "Disconnect"; enabled: appModel.connectionStatus !== "Disconnected"; onClicked: appModel.disconnect_vehicle() }
                    Item { Layout.fillWidth: true }
                    Label { text: appModel.connectionStatus; font.bold: true; color: appModel.connected ? "#18864b" : "#64748b" }
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
