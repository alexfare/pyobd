import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

ColumnLayout {
    id: root
    property bool editing: false
    property string selectedWidgetId: ""
    spacing: 0

    function colourValue(name) {
        const colours = {
            blue: "#2563eb", green: "#16a34a", orange: "#d97706",
            red: "#dc2626", purple: "#7e22ce", cyan: "#0891b2"
        }
        return colours[name] || colours.blue
    }

    function catalogIndex(pid) {
        const catalog = appModel.dashboardCatalog
        for (let index = 0; index < catalog.length; ++index)
            if (catalog[index].pid === pid) return index
        return 0
    }

    function openProperties(card) {
        selectedWidgetId = card.widgetId
        mainPidChoice.currentIndex = catalogIndex(card.pid)
        centerPidChoice.currentIndex = catalogIndex(card.centerPid || card.pid)
        sameCenterPid.checked = !card.centerPid
        titleField.text = card.title
        displayChoice.currentIndex = displayChoice.model.indexOf(card.style)
        shapeChoice.currentIndex = shapeChoice.model.indexOf(card.shape)
        colourChoice.currentIndex = colourChoice.model.indexOf(card.colour)
        minimumField.text = card.minimum.toString()
        maximumField.text = card.maximum.toString()
        divisionsSpin.value = card.divisions
        widthSpin.value = Math.round(card.width)
        heightSpin.value = Math.round(card.height)
        propertiesDialog.open()
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: root.editing ? 108 : 64
        Layout.minimumHeight: root.editing ? 108 : 64
        color: "#f3f6fa"
        ColumnLayout {
            anchors.fill: parent
            anchors.leftMargin: 18
            anchors.rightMargin: 18
            anchors.topMargin: 10
            anchors.bottomMargin: 10
            spacing: 6
            RowLayout {
                Layout.fillWidth: true
                ComboBox {
                    Layout.preferredWidth: 210
                    model: appModel.dashboardNames
                    currentIndex: Math.max(0, appModel.dashboardNames.indexOf(appModel.currentDashboard))
                    onActivated: appModel.select_dashboard(currentText)
                }
                Button { text: "New"; onClicked: newDashboardDialog.open() }
                Button { text: "Rename"; onClicked: { renameDashboardName.text = appModel.currentDashboard; renameDashboardDialog.open() } }
                Button { text: "Delete"; enabled: appModel.dashboardNames.length > 1; onClicked: deleteDashboardDialog.open() }
                Button { text: root.editing ? "Done" : "Edit Dashboard"; onClicked: root.editing = !root.editing }
                Item { Layout.fillWidth: true }
                Label { text: appModel.dashboardMessage; color: "#64748b"; elide: Text.ElideRight }
            }
            RowLayout {
                visible: root.editing
                Layout.fillWidth: true
                Button { text: "Add gauge"; onClicked: addDialog.open() }
                Button { text: "Clear all"; enabled: appModel.dashboardWidgets.length > 0; onClicked: clearDashboardDialog.open() }
                Button { text: "Import"; onClicked: importDialog.open() }
                Button { text: "Export"; onClicked: exportDialog.open() }
                Button { text: "Restore"; onClicked: appModel.restore_dashboard() }
                Item { Layout.fillWidth: true }
                Label { text: "Drag to move · use the blue corner to resize"; color: "#64748b" }
            }
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
                    required property string centerPid
                    required property string title
                    required property string style
                    required property string shape
                    required property string colour
                    required property real minimum
                    required property real maximum
                    required property int divisions
                    required property real xPosition
                    required property real yPosition
                    required property real widgetWidth
                    required property real widgetHeight
                    required property int layerValue
                    required property string readingValue
                    required property string centerReadingValue
                    required property string unit
                    required property string centerUnit
                    required property real numericValue
                    readonly property color accent: root.colourValue(colour)

                    x: xPosition
                    y: yPosition
                    width: widgetWidth
                    height: widgetHeight
                    z: layerValue
                    radius: shape === "circle" && !root.editing
                            ? Math.min(width, height) / 2
                            : (shape === "rectangle" ? 0 : 18)
                    color: "white"
                    border.width: root.editing ? 2 : 1
                    border.color: root.editing ? accent : "#dce3ec"

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
                        anchors.leftMargin: 14
                        anchors.rightMargin: 14
                        anchors.topMargin: 14
                        anchors.bottomMargin: 14
                        spacing: 6
                        RowLayout {
                            visible: card.shape !== "circle" || root.editing
                            Layout.fillWidth: true
                            Label { visible: card.shape !== "circle"; text: card.title; font.bold: true; color: "#172033"; Layout.fillWidth: true; elide: Text.ElideRight }
                            Label { visible: card.shape !== "circle"; text: card.pid; color: "#64748b"; font.pixelSize: 11 }
                            Item { visible: card.shape === "circle"; Layout.fillWidth: true }
                            ToolButton {
                                visible: root.editing
                                text: "Edit"
                                Layout.preferredWidth: 52
                                ToolTip.visible: hovered
                                ToolTip.text: "Gauge properties"
                                onClicked: root.openProperties(card)
                            }
                            ToolButton {
                                visible: root.editing
                                text: "×"
                                Layout.preferredWidth: 34
                                ToolTip.visible: hovered
                                ToolTip.text: "Delete gauge"
                                onClicked: appModel.remove_dashboard_widget(card.widgetId)
                            }
                        }

                        DashboardGauge {
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            visible: card.style !== "digital"
                            gaugeValue: card.numericValue
                            minimum: card.minimum
                            maximum: card.maximum
                            divisions: card.divisions
                            showDigital: card.style === "combined"
                            displayValue: card.centerReadingValue
                            unit: card.centerUnit
                            accent: card.accent
                        }

                        Column {
                            visible: card.style === "digital"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            Layout.alignment: Qt.AlignCenter
                            Label { anchors.horizontalCenter: parent.horizontalCenter; text: card.readingValue; font.pixelSize: 44; font.bold: true; color: "#172033" }
                            Label { anchors.horizontalCenter: parent.horizontalCenter; text: card.unit; color: "#64748b"; font.pixelSize: 16 }
                        }

                    }

                    Column {
                        visible: card.shape === "circle"
                        width: card.width * 0.62
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 10
                        spacing: 0
                        Label {
                            width: parent.width
                            text: card.title
                            font.bold: true
                            color: "#172033"
                            horizontalAlignment: Text.AlignHCenter
                            elide: Text.ElideRight
                        }
                        Label { width: parent.width; text: card.pid; color: "#64748b"; font.pixelSize: 10; horizontalAlignment: Text.AlignHCenter }
                    }

                    Rectangle {
                        id: rightResizeHandle
                        visible: root.editing && card.shape !== "circle"
                        width: 10
                        height: parent.height - 28
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        color: "transparent"
                        property real startWidth
                        property real startHeight
                        HoverHandler { cursorShape: Qt.SizeHorCursor }
                        DragHandler {
                            target: null
                            onActiveChanged: {
                                if (active) {
                                    rightResizeHandle.startWidth = card.width
                                    rightResizeHandle.startHeight = card.height
                                } else {
                                    appModel.set_dashboard_geometry(card.widgetId, card.x, card.y, card.width, card.height)
                                }
                            }
                            onActiveTranslationChanged: {
                                const minimum = card.style === "digital" ? 120 : 240
                                const size = Math.max(minimum, rightResizeHandle.startWidth + activeTranslation.x)
                                card.width = size
                            }
                        }
                    }

                    Rectangle {
                        id: bottomResizeHandle
                        visible: root.editing && card.shape !== "circle"
                        width: parent.width - 28
                        height: 10
                        anchors.bottom: parent.bottom
                        anchors.horizontalCenter: parent.horizontalCenter
                        color: "transparent"
                        property real startWidth
                        property real startHeight
                        HoverHandler { cursorShape: Qt.SizeVerCursor }
                        DragHandler {
                            target: null
                            onActiveChanged: {
                                if (active) {
                                    bottomResizeHandle.startWidth = card.width
                                    bottomResizeHandle.startHeight = card.height
                                } else {
                                    appModel.set_dashboard_geometry(card.widgetId, card.x, card.y, card.width, card.height)
                                }
                            }
                            onActiveTranslationChanged: {
                                const minimum = card.style === "digital" ? 100 : 240
                                const size = Math.max(minimum, bottomResizeHandle.startHeight + activeTranslation.y)
                                card.height = size
                            }
                        }
                    }

                    Rectangle {
                        id: cornerResizeHandle
                        visible: root.editing
                        width: 18
                        height: 18
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        radius: 5
                        color: card.accent
                        property real startWidth
                        property real startHeight
                        HoverHandler { cursorShape: Qt.SizeFDiagCursor }
                        DragHandler {
                            target: null
                            onActiveChanged: {
                                if (active) {
                                    cornerResizeHandle.startWidth = card.width
                                    cornerResizeHandle.startHeight = card.height
                                } else {
                                    appModel.set_dashboard_geometry(card.widgetId, card.x, card.y, card.width, card.height)
                                }
                            }
                            onActiveTranslationChanged: {
                                if (card.shape === "circle") {
                                    const delta = Math.abs(activeTranslation.x) >= Math.abs(activeTranslation.y) ? activeTranslation.x : activeTranslation.y
                                    const minimum = card.style === "digital" ? 120 : 240
                                    const size = Math.max(minimum, cornerResizeHandle.startWidth + delta)
                                    card.width = size
                                    card.height = size
                                } else {
                                    card.width = Math.max(card.style === "digital" ? 120 : 240, cornerResizeHandle.startWidth + activeTranslation.x)
                                    card.height = Math.max(card.style === "digital" ? 100 : 240, cornerResizeHandle.startHeight + activeTranslation.y)
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: newDashboardDialog
        anchors.centerIn: Overlay.overlay
        title: "New dashboard"
        modal: true
        standardButtons: Dialog.Save | Dialog.Cancel
        onAccepted: appModel.create_dashboard(newDashboardName.text)
        TextField { id: newDashboardName; width: 360; placeholderText: "Dashboard name" }
    }

    Dialog {
        id: renameDashboardDialog
        anchors.centerIn: Overlay.overlay
        title: "Rename dashboard"
        modal: true
        standardButtons: Dialog.Save | Dialog.Cancel
        onAccepted: appModel.rename_dashboard(renameDashboardName.text)
        TextField { id: renameDashboardName; width: 360 }
    }

    Dialog {
        id: deleteDashboardDialog
        anchors.centerIn: Overlay.overlay
        title: "Delete dashboard?"
        modal: true
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: appModel.delete_dashboard()
        Label { text: "Delete “" + appModel.currentDashboard + "”?" }
    }

    Dialog {
        id: clearDashboardDialog
        anchors.centerIn: Overlay.overlay
        title: "Clear dashboard?"
        modal: true
        standardButtons: Dialog.Yes | Dialog.No
        onAccepted: appModel.clear_dashboard()
        Label { text: "Remove every gauge from “" + appModel.currentDashboard + "”?" }
    }

    Dialog {
        id: propertiesDialog
        anchors.centerIn: Overlay.overlay
        width: 560
        height: 650
        modal: true
        title: "Gauge properties"
        standardButtons: Dialog.Save | Dialog.Cancel
        onAccepted: {
            const pid = mainPidChoice.currentValue || "010C"
            const centerPid = sameCenterPid.checked ? "" : (centerPidChoice.currentValue || pid)
            appModel.update_dashboard_properties(
                root.selectedWidgetId, pid, centerPid, titleField.text,
                displayChoice.currentText, shapeChoice.currentText,
                colourChoice.currentText, minimumField.text,
                maximumField.text, divisionsSpin.value
            )
            appModel.resize_dashboard_widget(root.selectedWidgetId, widthSpin.value, heightSpin.value)
        }

        GridLayout {
            anchors.fill: parent
            columns: 2
            rowSpacing: 10
            columnSpacing: 12

            Label { text: "Main PID" }
            ComboBox { id: mainPidChoice; Layout.fillWidth: true; model: appModel.dashboardCatalog; textRole: "name"; valueRole: "pid" }
            Label { text: "Widget name" }
            TextField { id: titleField; Layout.fillWidth: true }
            Label { text: "Display" }
            ComboBox { id: displayChoice; Layout.fillWidth: true; model: ["digital", "dial", "combined"] }
            Label { text: "Center PID"; visible: displayChoice.currentText === "combined" }
            ColumnLayout {
                visible: displayChoice.currentText === "combined"
                Layout.fillWidth: true
                CheckBox { id: sameCenterPid; text: "Same as main PID" }
                ComboBox { id: centerPidChoice; enabled: !sameCenterPid.checked; Layout.fillWidth: true; model: appModel.dashboardCatalog; textRole: "name"; valueRole: "pid" }
            }
            Label { text: "Shape" }
            ComboBox { id: shapeChoice; Layout.fillWidth: true; model: ["rounded", "circle", "rectangle"] }
            Label { text: "Colour" }
            ComboBox { id: colourChoice; Layout.fillWidth: true; model: ["blue", "green", "orange", "red", "purple", "cyan"] }
            Label { text: "Width" }
            SpinBox { id: widthSpin; Layout.fillWidth: true; from: displayChoice.currentText === "digital" ? 120 : 240; to: 800; editable: true }
            Label { text: "Height" }
            SpinBox { id: heightSpin; Layout.fillWidth: true; from: displayChoice.currentText === "digital" ? 100 : 240; to: 600; editable: true }
            Label { text: "Dial minimum"; visible: displayChoice.currentText !== "digital" }
            TextField { id: minimumField; visible: displayChoice.currentText !== "digital"; Layout.fillWidth: true }
            Label { text: "Dial maximum"; visible: displayChoice.currentText !== "digital" }
            TextField { id: maximumField; visible: displayChoice.currentText !== "digital"; Layout.fillWidth: true }
            Label { text: "Dial divisions"; visible: displayChoice.currentText !== "digital" }
            SpinBox { id: divisionsSpin; visible: displayChoice.currentText !== "digital"; Layout.fillWidth: true; from: 2; to: 20; editable: true }

            RowLayout {
                Layout.columnSpan: 2
                Layout.fillWidth: true
                Button { text: "Send to back"; onClicked: appModel.set_dashboard_layer_edge(root.selectedWidgetId, false) }
                Button { text: "Bring to front"; onClicked: appModel.set_dashboard_layer_edge(root.selectedWidgetId, true) }
                Item { Layout.fillWidth: true }
                Button {
                    text: "Delete gauge"
                    onClicked: {
                        appModel.remove_dashboard_widget(root.selectedWidgetId)
                        propertiesDialog.close()
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
