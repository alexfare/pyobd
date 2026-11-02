import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    spacing: 10
    RowLayout {
        Layout.fillWidth: true
        Layout.margins: 18
        Label { text: appModel.traceLines.length + " log entries"; color: "#64748b"; Layout.fillWidth: true }
        Button { text: "Refresh"; onClicked: appModel.refresh_trace() }
        Button { text: "Open log folder"; onClicked: appModel.open_app_link("logs") }
    }
    ListView {
        id: traceList
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 0
        Layout.margins: 18
        clip: true
        model: appModel.traceLines
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }
        delegate: Rectangle {
            required property int index
            required property string modelData
            width: traceList.width
            height: Math.max(38, line.implicitHeight + 14)
            color: index % 2 ? "#f8fafc" : "white"
            Label {
                id: line
                anchors.fill: parent
                anchors.margins: 7
                text: modelData
                color: "#172033"
                wrapMode: Text.WrapAnywhere
            }
        }
    }
}

