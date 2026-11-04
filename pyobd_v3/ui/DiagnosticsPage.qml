import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    spacing: 12

    function categoryCount(category) {
        let count = 0
        for (let index = 0; index < appModel.diagnosticCodes.length; ++index)
            if (appModel.diagnosticCodes[index].category === category) count++
        return count
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.margins: 18
        Button { text: "Scan codes"; highlighted: true; enabled: appModel.connected; onClicked: appModel.refresh_diagnostics() }
        Button { text: "Code lookup"; onClicked: lookupDialog.open() }
        Button { text: "Clear codes"; enabled: appModel.connected; onClicked: clearDialog.open() }
        Item { Layout.fillWidth: true }
        Label { text: appModel.diagnosticCodes.length + " codes"; color: "#64748b" }
    }
    RowLayout {
        Layout.fillWidth: true
        Layout.leftMargin: 18
        Layout.rightMargin: 18
        spacing: 12
        Repeater {
            model: [
                { name: "Stored", colour: "#b91c1c" },
                { name: "Pending", colour: "#c2410c" },
                { name: "Permanent", colour: "#2878f0" }
            ]
            delegate: Rectangle {
                required property var modelData
                Layout.fillWidth: true
                Layout.preferredHeight: 58
                radius: 10
                color: "white"
                border.color: "#dce3ec"
                RowLayout {
                    anchors.fill: parent
                    anchors.margins: 14
                    Label { text: modelData.name; color: "#64748b"; Layout.fillWidth: true }
                    Label { text: root.categoryCount(modelData.name); color: modelData.colour; font.pixelSize: 20; font.bold: true }
                }
            }
        }
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
    Dialog {
        id: lookupDialog
        property var results: []
        anchors.centerIn: Overlay.overlay
        width: Math.min(760, Overlay.overlay.width - 48)
        height: Math.min(620, Overlay.overlay.height - 48)
        title: "Diagnostic trouble code lookup"
        modal: true
        standardButtons: Dialog.Close
        onOpened: {
            lookupSearch.text = ""
            results = appModel.lookup_diagnostic_codes("")
            lookupSearch.forceActiveFocus()
        }
        ColumnLayout {
            anchors.fill: parent
            TextField {
                id: lookupSearch
                Layout.fillWidth: true
                placeholderText: "Search code or description"
                onTextChanged: lookupDialog.results = appModel.lookup_diagnostic_codes(text)
            }
            Label { text: lookupDialog.results.length + " codes"; color: "#64748b" }
            ListView {
                id: lookupList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 4
                model: lookupDialog.results
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                delegate: Rectangle {
                    required property var modelData
                    width: lookupList.width
                    height: 58
                    radius: 8
                    color: index % 2 ? "#f8fafc" : "white"
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        Label { text: modelData.code; font.bold: true; color: "#172033"; Layout.preferredWidth: 90 }
                        Label { text: modelData.description; color: "#334155"; wrapMode: Text.Wrap; Layout.fillWidth: true }
                    }
                }
            }
        }
    }
}
