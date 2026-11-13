import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
    id: root
    property string profileId: ""
    spacing: 12

    function loadProfile() {
        const profile = appModel.activeVehicleProfile
        profileId = profile.profile_id || ""
        vinField.text = profile.vin || ""
        nicknameField.text = profile.nickname || ""
        yearField.text = profile.year || ""
        makeField.text = profile.make || ""
        modelField.text = profile.model || ""
        notesField.text = profile.notes || ""
        const dashboard = profile.default_dashboard || ""
        defaultDashboard.currentIndex = dashboard ? Math.max(0, appModel.dashboardNames.indexOf(dashboard) + 1) : 0
    }

    Component.onCompleted: loadProfile()
    Connections { target: appModel; function onProfileChanged() { root.loadProfile() } }

    Rectangle {
        Layout.fillHeight: true
        Layout.preferredWidth: 280
        color: "white"
        border.color: "#dce3ec"
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 16
            Label { text: "Saved vehicles"; font.pixelSize: 20; font.bold: true; color: "#172033" }
            ListView {
                id: vehicleList
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                spacing: 8
                model: appModel.vehicleProfiles
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
                delegate: ItemDelegate {
                    required property var modelData
                    width: vehicleList.width
                    height: 64
                    highlighted: appModel.activeVehicleProfileID === modelData.profile_id
                    onClicked: appModel.select_vehicle_profile(modelData.profile_id)
                    contentItem: Column {
                        Label { text: modelData.display_name; font.bold: true; color: "#172033"; elide: Text.ElideRight; width: parent.width }
                        Label { text: modelData.vin || "No VIN"; color: "#64748b"; elide: Text.ElideRight; width: parent.width }
                    }
                }
            }
            Button { text: "New vehicle"; highlighted: true; Layout.fillWidth: true; onClicked: appModel.create_vehicle_profile() }
            Button { text: "Delete"; enabled: root.profileId.length > 0; Layout.fillWidth: true; onClicked: deleteDialog.open() }
        }
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        color: "white"
        border.color: "#dce3ec"
        ScrollView {
            anchors.fill: parent
            anchors.margins: 20
            clip: true
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ColumnLayout {
                width: parent.width
                spacing: 12
                Label { text: "Vehicle details"; font.pixelSize: 24; font.bold: true; color: "#172033" }
                Label { text: "Save information used to identify this vehicle and organize future sessions."; color: "#64748b"; wrapMode: Text.Wrap; Layout.fillWidth: true }
                GridLayout {
                    Layout.fillWidth: true
                    columns: 2
                    columnSpacing: 14
                    rowSpacing: 10
                    Label { text: "VIN" }
                    TextField { id: vinField; Layout.fillWidth: true; maximumLength: 17; enabled: root.profileId.length > 0 }
                    Label { text: "Nickname" }
                    TextField { id: nicknameField; Layout.fillWidth: true; enabled: root.profileId.length > 0 }
                    Label { text: "Year" }
                    TextField { id: yearField; Layout.fillWidth: true; maximumLength: 4; inputMethodHints: Qt.ImhDigitsOnly; enabled: root.profileId.length > 0 }
                    Label { text: "Make" }
                    TextField { id: makeField; Layout.fillWidth: true; enabled: root.profileId.length > 0 }
                    Label { text: "Model" }
                    TextField { id: modelField; Layout.fillWidth: true; enabled: root.profileId.length > 0 }
                }
                Label { text: "Notes" }
                TextArea { id: notesField; Layout.fillWidth: true; Layout.preferredHeight: 130; wrapMode: TextEdit.Wrap; enabled: root.profileId.length > 0 }
                Label { text: "Default dashboard" }
                ComboBox {
                    id: defaultDashboard
                    Layout.fillWidth: true
                    enabled: root.profileId.length > 0
                    model: ["No default"].concat(appModel.dashboardNames)
                }
                RowLayout {
                    Layout.fillWidth: true
                    Button {
                        text: "Save profile"
                        highlighted: true
                        enabled: root.profileId.length > 0
                        onClicked: appModel.save_vehicle_profile(
                            root.profileId, vinField.text, nicknameField.text,
                            yearField.text, makeField.text, modelField.text,
                            notesField.text,
                            defaultDashboard.currentIndex > 0 ? defaultDashboard.currentText : ""
                        )
                    }
                    Label { text: appModel.vehicleProfileStatus; color: "#64748b"; Layout.fillWidth: true }
                }
            }
        }
    }

    Dialog {
        id: deleteDialog
        anchors.centerIn: Overlay.overlay
        title: "Delete vehicle profile?"
        modal: true
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: appModel.delete_vehicle_profile(root.profileId)
        Label { text: "This vehicle profile will be permanently removed." }
    }
}
