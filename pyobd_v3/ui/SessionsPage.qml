import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

ColumnLayout {
    id: root
    property var selectedSession: ({})
    spacing: 10

    function durationLabel(value) {
        const total = Math.max(0, Math.floor(Number(value) || 0))
        const hours = Math.floor(total / 3600)
        const minutes = Math.floor((total % 3600) / 60)
        const seconds = total % 60
        return (hours ? String(hours).padStart(2, "0") + ":" : "") + String(minutes).padStart(2, "0") + ":" + String(seconds).padStart(2, "0")
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.margins: 18
        Label { text: appModel.recordedSessions.length + " recorded sessions"; color: "#64748b"; Layout.fillWidth: true }
        Label { text: appModel.replayStatus; color: "#64748b" }
        Button { text: appModel.replayActive ? "Stop" : "Replay"; enabled: appModel.replayActive || !!selectedSession.csv_path; onClicked: appModel.replayActive ? appModel.stop_session_replay() : appModel.start_session_replay(selectedSession.csv_path) }
        Button { text: "Rename"; enabled: !!selectedSession.csv_path; onClicked: { renameField.text = selectedSession.name || ""; renameDialog.open() } }
        Button { text: "Export"; enabled: !!selectedSession.csv_path; onClicked: exportDialog.open() }
        Button { text: "Delete"; enabled: !!selectedSession.csv_path; onClicked: deleteDialog.open() }
        Button { text: "Open folder"; onClicked: appModel.open_app_link("recordings") }
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.leftMargin: 18
        Layout.rightMargin: 18
        Layout.preferredHeight: 38
        color: "#e7edf5"
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 14
            anchors.rightMargin: 14
            Label { text: "Session"; Layout.fillWidth: true; font.bold: true; color: "#64748b" }
            Label { text: "Vehicle"; Layout.preferredWidth: 170; font.bold: true; color: "#64748b" }
            Label { text: "Recorded"; Layout.preferredWidth: 190; font.bold: true; color: "#64748b" }
            Label { text: "Samples"; Layout.preferredWidth: 80; font.bold: true; color: "#64748b"; horizontalAlignment: Text.AlignRight }
            Label { text: "Duration"; Layout.preferredWidth: 90; font.bold: true; color: "#64748b"; horizontalAlignment: Text.AlignRight }
        }
    }

    ListView {
        id: sessionList
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 0
        Layout.leftMargin: 18
        Layout.rightMargin: 18
        Layout.bottomMargin: 18
        clip: true
        model: appModel.recordedSessions
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }
        delegate: ItemDelegate {
            required property int index
            required property var modelData
            width: sessionList.width
            height: 62
            highlighted: root.selectedSession.csv_path === modelData.csv_path
            onClicked: root.selectedSession = modelData
            contentItem: RowLayout {
                Label { text: modelData.name || "Untitled session"; Layout.fillWidth: true; font.bold: true; elide: Text.ElideRight }
                Label { text: modelData.vehicle || "Unassigned"; Layout.preferredWidth: 170; elide: Text.ElideRight; color: "#64748b" }
                Label { text: modelData.started_at || "Unknown"; Layout.preferredWidth: 190; elide: Text.ElideRight; color: "#64748b" }
                Label { text: modelData.samples || 0; Layout.preferredWidth: 80; horizontalAlignment: Text.AlignRight }
                Label { text: root.durationLabel(modelData.duration_seconds); Layout.preferredWidth: 90; horizontalAlignment: Text.AlignRight }
            }
        }
    }

    Dialog {
        id: renameDialog
        anchors.centerIn: Overlay.overlay
        title: "Rename session"
        modal: true
        standardButtons: Dialog.Save | Dialog.Cancel
        onAccepted: appModel.rename_session(root.selectedSession.csv_path, renameField.text)
        TextField { id: renameField; width: 360 }
    }
    Dialog {
        id: deleteDialog
        anchors.centerIn: Overlay.overlay
        title: "Delete session?"
        modal: true
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: { appModel.delete_session(root.selectedSession.csv_path); root.selectedSession = ({}) }
        Label { text: "Delete “" + (root.selectedSession.name || "Untitled session") + "”?" }
    }
    FileDialog {
        id: exportDialog
        title: "Export recorded session"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "csv"
        nameFilters: ["CSV files (*.csv)"]
        onAccepted: appModel.export_session(root.selectedSession.csv_path, selectedFile.toString())
    }
}

