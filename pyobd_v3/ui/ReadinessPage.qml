import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    property int readyCount: 0
    property int notReadyCount: 0
    property int unsupportedCount: 0
    spacing: 10

    function updateCounts() {
        let ready = 0, notReady = 0, unsupported = 0
        const rows = appModel.readinessResults
        for (let index = 0; index < rows.length; ++index) {
            if (rows[index].status === "Ready") ready++
            else if (rows[index].status === "Not ready") notReady++
            else unsupported++
        }
        readyCount = ready
        notReadyCount = notReady
        unsupportedCount = unsupported
    }

    Connections { target: appModel; function onDiagnosticsChanged() { root.updateCounts() } }
    Component.onCompleted: updateCounts()

    RowLayout {
        Layout.fillWidth: true
        Layout.margins: 18
        Label {
            text: tabs.currentIndex === 0 ? "Readiness monitor status" : "Mode 06 misfire results"
            color: "#64748b"
            Layout.fillWidth: true
        }
        Button {
            text: "Refresh"
            highlighted: true
            enabled: appModel.connected
            onClicked: tabs.currentIndex === 0 ? appModel.refresh_readiness() : appModel.refresh_misfire()
        }
    }

    TabBar {
        id: tabs
        Layout.fillWidth: true
        Layout.leftMargin: 18
        Layout.rightMargin: 18
        TabButton { text: "Readiness" }
        TabButton { text: "Misfire Results"; onClicked: if (appModel.connected) appModel.refresh_misfire() }
    }

    StackLayout {
        currentIndex: tabs.currentIndex
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 0

        ColumnLayout {
            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                Repeater {
                    model: [
                        {name: "Ready", count: root.readyCount, colour: "#18864b"},
                        {name: "Not Ready", count: root.notReadyCount, colour: "#c2410c"},
                        {name: "Unsupported", count: root.unsupportedCount, colour: "#64748b"}
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
                            Label { text: modelData.count; color: modelData.colour; font.pixelSize: 20; font.bold: true }
                        }
                    }
                }
            }
            Label {
                text: "Readiness shows which emissions monitors have completed. Clearing diagnostic codes resets readiness."
                color: "#64748b"
                Layout.fillWidth: true
                Layout.leftMargin: 18
                Layout.rightMargin: 18
                wrapMode: Text.Wrap
            }
            GridView {
                id: readinessGrid
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 0
                Layout.margins: 18
                clip: true
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }
                cellWidth: Math.max(280, width / 3)
                cellHeight: 112
                model: appModel.readinessResults
                delegate: Item {
                    required property var modelData
                    width: readinessGrid.cellWidth
                    height: readinessGrid.cellHeight
                    Rectangle {
                        anchors.fill: parent
                        anchors.margins: 5
                        radius: 14
                        color: "white"
                        border.color: "#dce3ec"
                        ColumnLayout {
                            anchors.fill: parent
                            anchors.margins: 15
                            Label { text: modelData.name; font.bold: true; color: "#172033"; wrapMode: Text.Wrap; Layout.fillWidth: true }
                            Item { Layout.fillHeight: true }
                            Label { text: modelData.status; color: modelData.status === "Ready" ? "#18864b" : modelData.status === "Not ready" ? "#c2410c" : "#64748b"; font.bold: true }
                        }
                    }
                }
            }
        }

        ColumnLayout {
            Label {
                text: "Mode 06 misfire results are shown only for cylinder monitors supported by the vehicle."
                color: "#64748b"
                Layout.fillWidth: true
                Layout.margins: 18
                wrapMode: Text.Wrap
            }
            ListView {
                id: misfireList
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 0
                Layout.margins: 18
                clip: true
                spacing: 8
                model: appModel.misfireResults
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }
                delegate: Rectangle {
                    required property var modelData
                    width: misfireList.width
                    height: 68
                    radius: 12
                    color: "white"
                    border.color: "#dce3ec"
                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        Label { text: "Cylinder " + modelData.cylinder; font.bold: true; color: "#172033"; Layout.fillWidth: true }
                        Label { text: modelData.result; font.bold: true; color: modelData.count === 0 ? "#18864b" : "#c2410c" }
                    }
                }
                Label {
                    anchors.centerIn: parent
                    visible: misfireList.count === 0
                    text: appModel.connected ? "No supported per-cylinder misfire monitors" : "Connect to read misfire monitors"
                    color: "#64748b"
                }
            }
        }
    }
}
