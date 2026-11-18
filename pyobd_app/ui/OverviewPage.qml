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
                            Label { text: modelData.pid || modelData.type; color: "#64748b"; font.pixelSize: 11 }
                        }

                        Row {
                            visible: modelData.type === "pid"
                            spacing: 8
                            Label { text: modelData.value; color: modelData.available ? "#172033" : "#94a3b8"; font.pixelSize: 38; font.bold: true }
                            Label { anchors.baseline: parent.children[0].baseline; text: modelData.unit; color: "#64748b" }
                        }

                        ProgressBar {
                            visible: modelData.type === "pid"
                            Layout.fillWidth: true
                            value: modelData.progress
                        }

                        Canvas {
                            id: compactGraph
                            visible: modelData.type === "graph"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            onWidthChanged: requestPaint()
                            onHeightChanged: requestPaint()
                            onPaint: {
                                const ctx = getContext("2d")
                                ctx.reset()
                                const points = appModel.graph_points(modelData.pid)
                                if (points.length < 2) return
                                let low = Math.min.apply(null, points)
                                let high = Math.max.apply(null, points)
                                if (high <= low) high = low + 1
                                ctx.strokeStyle = "#2878f0"
                                ctx.lineWidth = 3
                                ctx.beginPath()
                                for (let i = 0; i < points.length; ++i) {
                                    const x = i * width / Math.max(1, points.length - 1)
                                    const y = height - ((points[i] - low) / (high - low)) * height
                                    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
                                }
                                ctx.stroke()
                            }
                            Connections {
                                target: appModel
                                function onGraphChanged() { compactGraph.requestPaint() }
                            }
                        }

                        Label {
                            visible: modelData.type !== "pid" && modelData.type !== "graph" && modelData.type !== "shortcut"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            text: modelData.value || "Unavailable"
                            color: modelData.available ? "#172033" : "#94a3b8"
                            font.pixelSize: 28
                            font.bold: true
                            verticalAlignment: Text.AlignVCenter
                            elide: Text.ElideRight
                        }

                        Button {
                            visible: modelData.type === "shortcut"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            text: "Open " + modelData.value
                            onClicked: appModel.open_shortcut(modelData.value)
                        }

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
