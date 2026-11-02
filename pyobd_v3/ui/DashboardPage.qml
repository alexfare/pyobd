import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

ColumnLayout {
    id: root
    property bool editing: false
    spacing: 0

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 64
        Layout.minimumHeight: 64
        color: "#f3f6fa"
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 18
            anchors.rightMargin: 18
            Button { text: root.editing ? "Done" : "Edit Dashboard"; onClicked: root.editing = !root.editing }
            Button { text: "Add gauge"; visible: root.editing; onClicked: addDialog.open() }
            Button { text: "Import"; visible: root.editing; onClicked: importDialog.open() }
            Button { text: "Export"; visible: root.editing; onClicked: exportDialog.open() }
            Button { text: "Restore"; visible: root.editing; onClicked: appModel.restore_dashboard() }
            Item { Layout.fillWidth: true }
            Label { text: appModel.dashboardMessage; color: "#64748b" }
        }
    }

    Flickable {
        id: viewport
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 0
        contentWidth: Math.max(width, 1800)
        contentHeight: Math.max(height, 1100)
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AlwaysOn }
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }

        Item {
            id: board
            width: viewport.contentWidth
            height: viewport.contentHeight

            Repeater {
                model: appModel.dashboardModel
                delegate: Rectangle {
                    id: card
                    required property string widgetId
                    required property string pid
                    required property string title
                    required property string style
                    required property real minimum
                    required property real maximum
                    required property real xPosition
                    required property real yPosition
                    required property real widgetWidth
                    required property real widgetHeight
                    required property int layerValue
                    required property string readingValue
                    required property string unit
                    required property real numericValue

                    x: xPosition
                    y: yPosition
                    width: widgetWidth
                    height: widgetHeight
                    z: layerValue
                    radius: 18
                    color: "white"
                    border.width: root.editing ? 2 : 1
                    border.color: root.editing ? "#2878f0" : "#dce3ec"

                    DragHandler {
                        target: card
                        enabled: root.editing
                        xAxis.minimum: 0
                        xAxis.maximum: board.width - card.width
                        yAxis.minimum: 0
                        yAxis.maximum: board.height - card.height
                        onActiveChanged: if (!active) appModel.move_dashboard_widget(card.widgetId, card.x, card.y)
                    }

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 6
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: card.title; font.bold: true; color: "#172033"; Layout.fillWidth: true; elide: Text.ElideRight }
                            Label { text: card.pid; color: "#64748b"; font.pixelSize: 11 }
                        }

                        DashboardGauge {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            visible: card.style !== "digital"
                            gaugeValue: card.numericValue
                            minimum: card.minimum
                            maximum: card.maximum
                            showDigital: card.style === "combined"
                            displayValue: card.readingValue
                            unit: card.unit
                        }

                        Column {
                            visible: card.style === "digital"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.alignment: Qt.AlignCenter
                            Label { anchors.horizontalCenter: parent.horizontalCenter; text: card.readingValue; font.pixelSize: 44; font.bold: true; color: "#172033" }
                            Label { anchors.horizontalCenter: parent.horizontalCenter; text: card.unit; color: "#64748b"; font.pixelSize: 16 }
                        }

                        RowLayout {
                            visible: root.editing
                            Layout.fillWidth: true
                            ComboBox {
                                Layout.preferredWidth: 110
                                model: ["digital", "dial", "combined"]
                                currentIndex: Math.max(0, model.indexOf(card.style))
                                onActivated: appModel.set_dashboard_style(card.widgetId, currentText)
                            }
                            TextField { id: minimumField; Layout.preferredWidth: 62; text: card.minimum.toString(); placeholderText: "Min"; onEditingFinished: appModel.set_dashboard_range(card.widgetId, text, maximumField.text) }
                            TextField { id: maximumField; Layout.preferredWidth: 70; text: card.maximum.toString(); placeholderText: "Max"; onEditingFinished: appModel.set_dashboard_range(card.widgetId, minimumField.text, text) }
                            Button { text: "↓"; onClicked: appModel.change_dashboard_layer(card.widgetId, -1) }
                            Button { text: "↑"; onClicked: appModel.change_dashboard_layer(card.widgetId, 1) }
                            Button { text: "×"; onClicked: appModel.remove_dashboard_widget(card.widgetId) }
                        }
                    }

                    Rectangle {
                        id: resizeHandle
                        visible: root.editing
                        width: 24
                        height: 24
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        radius: 6
                        color: "#2878f0"
                        property real startWidth
                        property real startHeight
                        DragHandler {
                            id: resizeDrag
                            target: null
                            onActiveChanged: {
                                if (active) {
                                    resizeHandle.startWidth = card.width
                                    resizeHandle.startHeight = card.height
                                } else {
                                    appModel.resize_dashboard_widget(card.widgetId, card.width, card.height)
                                }
                            }
                            onActiveTranslationChanged: {
                                card.width = Math.max(220, resizeHandle.startWidth + activeTranslation.x)
                                card.height = Math.max(170, resizeHandle.startHeight + activeTranslation.y)
                            }
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: addDialog
        anchors.centerIn: Overlay.overlay
        width: 520
        height: 560
        modal: true
        title: "Add dashboard gauge"
        standardButtons: Dialog.Close
        ListView {
            anchors.fill: parent
            model: appModel.dashboardCatalog
            clip: true
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AlwaysOn }
            delegate: ItemDelegate {
                required property var modelData
                width: ListView.view.width
                text: modelData.name + "  ·  " + modelData.pid
                onClicked: { appModel.add_dashboard_widget(modelData.pid); addDialog.close() }
            }
        }
    }

    FileDialog {
        id: importDialog
        title: "Import dashboard"
        fileMode: FileDialog.OpenFile
        nameFilters: ["pyOBD Dashboard (*.pyOBD)", "JSON files (*.json)"]
        onAccepted: appModel.import_dashboard(selectedFile.toString())
    }
    FileDialog {
        id: exportDialog
        title: "Export dashboard"
        fileMode: FileDialog.SaveFile
        defaultSuffix: "pyOBD"
        nameFilters: ["pyOBD Dashboard (*.pyOBD)"]
        onAccepted: appModel.export_dashboard(selectedFile.toString())
    }
}
