import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    spacing: 0

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 74
        Layout.minimumHeight: 74
        color: "#f3f6fa"
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 20
            anchors.rightMargin: 20
            spacing: 12
            TextField {
                id: search
                Layout.fillWidth: true
                placeholderText: "Search by sensor name or PID"
                onTextChanged: appModel.set_live_filter(text, favorites.checked)
            }
            CheckBox {
                id: favorites
                text: "Favorites only"
                onToggled: appModel.set_live_filter(search.text, checked)
            }
            Label { text: appModel.selectedLiveCount + " selected"; color: "#64748b" }
            Button { text: "Clear"; enabled: appModel.selectedLiveCount > 0 && !appModel.recordingActive; onClicked: appModel.clear_live_selection() }
            Button {
                text: appModel.recordingActive ? "Stop recording" : "Record selected"
                enabled: appModel.recordingActive || appModel.selectedLiveCount > 0
                highlighted: appModel.recordingActive
                onClicked: appModel.recordingActive ? appModel.stop_recording() : recordingDialog.open()
            }
        }
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.leftMargin: 20
        Layout.rightMargin: 20
        Layout.preferredHeight: 38
        Layout.minimumHeight: 38
        color: "#e7edf5"
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 18
            spacing: 12
            Item { Layout.preferredWidth: 34 }
            Item { Layout.preferredWidth: 38 }
            Label { text: "PID"; Layout.preferredWidth: 72; color: "#64748b"; font.bold: true }
            Label { text: "Sensor"; Layout.fillWidth: true; color: "#64748b"; font.bold: true }
            Label { text: "Value"; Layout.preferredWidth: 180; horizontalAlignment: Text.AlignRight; color: "#64748b"; font.bold: true }
        }
    }

    ListView {
        id: liveList
        objectName: "liveDataList"
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 0
        Layout.leftMargin: 20
        Layout.rightMargin: 20
        Layout.bottomMargin: 16
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        model: appModel.liveDataModel
        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AlwaysOn
            width: 12
            contentItem: Rectangle { radius: 4; color: "#94a3b8" }
            background: Rectangle { color: "#e2e8f0" }
        }

        delegate: Rectangle {
            required property int index
            required property string pid
            required property string sensorName
            required property string readingValue
            required property string unit
            required property bool favorite
            required property bool selected
            width: liveList.width
            height: 62
            color: index % 2 ? "#f8fafc" : "white"
            border.color: "#e8edf4"
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 12
                anchors.rightMargin: 18
                spacing: 12
                CheckBox {
                    Layout.preferredWidth: 34
                    checked: selected
                    enabled: !appModel.recordingActive
                    onClicked: appModel.toggle_live_selection(pid)
                }
                Button {
                    Layout.preferredWidth: 38
                    Layout.preferredHeight: 38
                    text: favorite ? "★" : "☆"
                    flat: true
                    onClicked: appModel.toggle_favorite(pid)
                }
                Label {
                    Layout.preferredWidth: 72
                    text: pid
                    color: "#64748b"
                    font.family: "monospace"
                }
                Label {
                    Layout.fillWidth: true
                    text: sensorName
                    color: "#172033"
                    font.bold: true
                    elide: Text.ElideRight
                }
                Label {
                    Layout.preferredWidth: 180
                    text: readingValue + (unit.length ? " " + unit : "")
                    horizontalAlignment: Text.AlignRight
                    color: "#172033"
                    font.pixelSize: 17
                    font.bold: true
                }
            }
        }

        Label {
            anchors.centerIn: parent
            visible: liveList.count === 0
            text: appModel.connected ? "No supported PIDs match this filter" : "Connect an adapter to view live data"
            color: "#64748b"
            font.pixelSize: 16
        }
    }

    Dialog {
        id: recordingDialog
        anchors.centerIn: Overlay.overlay
        width: 440
        modal: true
        title: "New live-data recording"
        standardButtons: Dialog.Save | Dialog.Cancel
        onAccepted: appModel.start_recording(recordingName.text)
        ColumnLayout {
            anchors.fill: parent
            Label { text: "Recording name"; font.bold: true }
            TextField { id: recordingName; Layout.fillWidth: true; text: "Live Data Session"; selectByMouse: true }
            Label { text: appModel.selectedLiveCount + " PID(s) will be recorded to CSV"; color: "#64748b" }
        }
    }

    Label {
        visible: appModel.recordingStatus.length > 0
        text: appModel.recordingStatus
        color: "#64748b"
        Layout.leftMargin: 20
        Layout.bottomMargin: 8
    }
}
