import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    spacing: 12
    RowLayout {
        Layout.fillWidth: true
        Layout.margins: 18
        Button { text: "Load freeze frame"; highlighted: true; enabled: appModel.connected; onClicked: appModel.refresh_freeze_frame() }
        Item { Layout.fillWidth: true }
        Label { text: appModel.freezeFrameResults.length + " values"; color: "#64748b" }
    }
    ListView {
        id: freezeList
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 0
        Layout.margins: 18
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }
        model: appModel.freezeFrameResults
        delegate: Rectangle {
            required property int index
            required property var modelData
            width: freezeList.width
            height: 58
            color: index % 2 ? "#f8fafc" : "white"
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 14
                anchors.rightMargin: 14
                Label { text: modelData.pid; color: "#64748b"; Layout.preferredWidth: 72 }
                Label { text: modelData.name; color: "#172033"; font.bold: true; Layout.fillWidth: true }
                Label { text: modelData.value; color: "#172033"; font.pixelSize: 16 }
            }
        }
    }
}
