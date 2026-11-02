import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root
    property bool editing: false
    clip: true
    contentWidth: availableWidth
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
    ScrollBar.vertical.policy: ScrollBar.AsNeeded

    ColumnLayout {
        width: root.availableWidth
        spacing: 14

        RowLayout {
            Layout.fillWidth: true
            Layout.margins: 24
            Button { text: root.editing ? "Done" : "Edit Overview"; onClicked: root.editing = !root.editing }
            Button { text: "Add widget"; visible: root.editing; onClicked: addDialog.open() }
            Button { text: "Restore default"; visible: root.editing; onClicked: appModel.restore_overview() }
            CheckBox {
                visible: root.editing && appModel.vin !== "----"
                text: "Layout for this vehicle"
                checked: appModel.vehicleLayoutEnabled
                onToggled: appModel.set_vehicle_layout_enabled(checked)
            }
            Item { Layout.fillWidth: true }
            Label { text: appModel.vin === "----" ? "No vehicle identified" : appModel.vin; color: "#64748b" }
        }

        Flow {
            id: widgetFlow
            Layout.fillWidth: true
            Layout.leftMargin: 24
            Layout.rightMargin: 24
            spacing: 14

            Repeater {
                model: appModel.overviewWidgets
                delegate: Rectangle {
                    required property int index
                    required property var modelData
                    width: modelData.size === "wide" ? widgetFlow.width : (widgetFlow.width - widgetFlow.spacing) / 2
                    height: root.editing ? 226 : 190
                    radius: 16
                    color: "white"
                    border.color: "#dce3ec"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 18
                        spacing: 8
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: modelData.title; color: "#172033"; font.pixelSize: 16; font.bold: true; Layout.fillWidth: true }
                            Label { text: modelData.pid; color: "#64748b"; font.pixelSize: 11 }
                        }
                        Row {
                            spacing: 8
                            Label { text: modelData.value; color: modelData.available ? "#172033" : "#94a3b8"; font.pixelSize: 38; font.bold: true }
                            Label { anchors.baseline: parent.children[0].baseline; text: modelData.unit; color: "#64748b" }
                        }
                        ProgressBar { Layout.fillWidth: true; value: modelData.progress }
                        Item { Layout.fillHeight: true }
                        RowLayout {
                            visible: root.editing
                            Layout.fillWidth: true
                            Button { text: "←"; enabled: index > 0; onClicked: appModel.move_overview_widget(index, -1) }
                            Button { text: "→"; enabled: index + 1 < appModel.overviewWidgets.length; onClicked: appModel.move_overview_widget(index, 1) }
                            Button { text: modelData.size === "wide" ? "Make small" : "Make wide"; onClicked: appModel.toggle_overview_widget_size(index) }
                            Item { Layout.fillWidth: true }
                            Button { text: "Remove"; onClicked: appModel.remove_overview_widget(index) }
                        }
                    }
                }
            }
        }
        Item { Layout.preferredHeight: 24 }
    }

    Dialog {
        id: addDialog
        anchors.centerIn: Overlay.overlay
        width: 520
        height: 560
        modal: true
        title: "Add Overview widget"
        standardButtons: Dialog.Close
        ListView {
            anchors.fill: parent
            clip: true
            model: appModel.widgetCatalog
            delegate: ItemDelegate {
                required property var modelData
                width: ListView.view.width
                text: modelData.name + "  ·  " + modelData.pid
                onClicked: { appModel.add_overview_widget(modelData.pid); addDialog.close() }
            }
        }
    }
}
