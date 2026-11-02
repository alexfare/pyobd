import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    spacing: 12
    RowLayout {
        Layout.fillWidth: true
        Layout.margins: 18
        Button { text: "Scan codes"; highlighted: true; enabled: appModel.connected; onClicked: appModel.refresh_diagnostics() }
        Button { text: "Clear codes"; enabled: appModel.connected; onClicked: clearDialog.open() }
        Item { Layout.fillWidth: true }
        Label { text: appModel.diagnosticCodes.length + " codes"; color: "#64748b" }
    }
    ListView {
        id: diagnosticList
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 0
        Layout.margins: 18
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }
        spacing: 8
        model: appModel.diagnosticCodes
        delegate: Rectangle {
            required property var modelData
            width: diagnosticList.width
            height: 84
            radius: 12
            color: "white"
            border.color: "#dce3ec"
            RowLayout {
                anchors.fill: parent
                anchors.margins: 14
                Label { text: modelData.code; font.pixelSize: 20; font.bold: true; color: "#b91c1c"; Layout.preferredWidth: 100 }
                ColumnLayout {
                    Layout.fillWidth: true
                    Label { text: modelData.description; font.bold: true; color: "#172033"; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    Label { text: modelData.category; color: "#64748b" }
                }
            }
        }
    }
    Dialog {
        id: clearDialog
        anchors.centerIn: Overlay.overlay
        title: "Clear diagnostic codes?"
        modal: true
        standardButtons: Dialog.Cancel | Dialog.Ok
        onAccepted: appModel.clear_diagnostics()
        Label { text: "This also resets readiness monitors and may remove freeze-frame data."; wrapMode: Text.Wrap; width: 420 }
    }
}
