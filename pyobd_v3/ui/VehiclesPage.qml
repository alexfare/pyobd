import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    spacing: 12
    RowLayout {
        Layout.fillWidth: true
        Layout.margins: 18
        TextField { id: nickname; Layout.preferredWidth: 220; placeholderText: "Vehicle nickname" }
        TextField { id: vin; Layout.fillWidth: true; placeholderText: "VIN"; text: appModel.vin === "----" ? "" : appModel.vin }
        ComboBox { id: defaultPage; model: ["Overview", "Dashboard"] }
        Button {
            text: "Add vehicle"
            highlighted: true
            enabled: nickname.text.trim().length > 0
            onClicked: {
                appModel.add_vehicle_profile(nickname.text, vin.text, defaultPage.currentText)
                nickname.clear()
            }
        }
    }
    ListView {
        id: vehicleList
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 0
        Layout.margins: 18
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }
        spacing: 8
        model: appModel.vehicleProfiles
        delegate: Rectangle {
            required property var modelData
            width: vehicleList.width
            height: 78
            radius: 12
            color: appModel.activeVehicleProfileID === modelData.profile_id ? "#eaf2ff" : "white"
            border.color: appModel.activeVehicleProfileID === modelData.profile_id ? "#2878f0" : "#dce3ec"
            RowLayout {
                anchors.fill: parent
                anchors.margins: 14
                ColumnLayout {
                    Layout.fillWidth: true
                    Label { text: modelData.nickname; font.pixelSize: 17; font.bold: true; color: "#172033" }
                    Label { text: (modelData.vin || "No VIN") + "  ·  Default: " + modelData.default_dashboard; color: "#64748b" }
                }
                Button { text: "Select"; onClicked: appModel.select_vehicle_profile(modelData.profile_id) }
                Button { text: "Delete"; onClicked: appModel.delete_vehicle_profile(modelData.profile_id) }
            }
        }
    }
}
