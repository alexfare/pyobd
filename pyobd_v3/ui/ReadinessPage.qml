import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    spacing: 12
    RowLayout {
        Layout.fillWidth: true
        Layout.margins: 18
        Button { text: "Refresh readiness"; highlighted: true; enabled: appModel.connected; onClicked: appModel.refresh_readiness() }
        Item { Layout.fillWidth: true }
        Label { text: appModel.readinessResults.length + " monitors"; color: "#64748b" }
    }
    GridView {
        id: readinessGrid
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 0
        Layout.margins: 18
        clip: true
        boundsBehavior: Flickable.StopAtBounds
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
                    Label {
                        text: modelData.status
                        color: modelData.status === "Ready" ? "#18864b" : modelData.status === "Not ready" ? "#c2410c" : "#64748b"
                        font.bold: true
                    }
                }
            }
        }
    }
}
