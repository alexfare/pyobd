import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    readonly property var graphPids: appModel.graphPids
    property bool paused: false
    property bool combinedView: false
    readonly property var graphColours: ["#2878f0", "#16a34a", "#d97706", "#7e22ce", "#0891b2", "#dc2626"]
    spacing: 0

    Label { id: fontProbe; visible: false }

    function addGraph(pid) {
        appModel.add_graph_pid(pid)
    }

    function removeGraph(index) {
        appModel.remove_graph_pid(index)
    }

    function pidName(pid) {
        const catalog = appModel.dashboardCatalog
        for (let index = 0; index < catalog.length; ++index)
            if (catalog[index].pid === pid) return catalog[index].name
        return pid
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 112
        color: "#f3f6fa"
        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            RowLayout {
                Layout.fillWidth: true
                Label { text: "Add live graph"; font.bold: true; color: "#172033" }
                ComboBox {
                    id: pidSelector
                    Layout.preferredWidth: 320
                    model: appModel.dashboardCatalog
                    textRole: "name"
                    valueRole: "pid"
                }
                Button { text: "Add"; onClicked: root.addGraph(pidSelector.currentValue) }
                Button {
                    text: root.paused ? "Resume" : "Pause"
                    enabled: root.graphPids.length > 0
                    onClicked: root.paused = !root.paused
                }
                Button {
                    text: root.combinedView ? "Separate graphs" : "Combined graph"
                    enabled: root.graphPids.length > 1
                    onClicked: root.combinedView = !root.combinedView
                }
                Item { Layout.fillWidth: true }
                Label { text: root.graphPids.length + (root.graphPids.length === 1 ? " graph" : " graphs"); color: "#64748b" }
            }
            RowLayout {
                Layout.fillWidth: true
                Label { text: "Preset"; color: "#64748b" }
                ComboBox {
                    id: presetChoice
                    Layout.preferredWidth: 220
                    model: ["Select preset"].concat(appModel.graphPresetNames)
                    onActivated: if (currentIndex > 0) appModel.select_graph_preset(currentText)
                    Connections {
                        target: appModel
                        function onGraphSelectionChanged() {
                            const name = appModel.currentGraphPreset
                            presetChoice.currentIndex = name.length ? presetChoice.find(name) : 0
                        }
                    }
                }
                Button { text: "Save as"; enabled: root.graphPids.length > 0; onClicked: savePresetDialog.open() }
                Button { text: "Rename"; enabled: appModel.currentGraphPreset.length > 0; onClicked: { presetName.text = appModel.currentGraphPreset; renamePresetDialog.open() } }
                Button { text: "Delete"; enabled: appModel.currentGraphPreset.length > 0; onClicked: deletePresetDialog.open() }
                Item { Layout.fillWidth: true }
            }
        }
    }

    ScrollView {
        id: graphScroll
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 0
        clip: true
        contentWidth: availableWidth
        ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
        ScrollBar.vertical.policy: ScrollBar.AsNeeded

        Flow {
            id: graphFlow
            width: graphScroll.availableWidth
            padding: 18
            spacing: 14

            Rectangle {
                id: combinedCard
                visible: root.combinedView && root.graphPids.length > 0
                width: visible ? graphFlow.width - graphFlow.leftPadding - graphFlow.rightPadding : 0
                height: visible ? 420 : 0
                radius: 16
                color: "white"
                border.color: "#dce3ec"
                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    Flow {
                        Layout.fillWidth: true
                        spacing: 14
                        Repeater {
                            model: root.graphPids
                            delegate: Row {
                                required property int index
                                required property string modelData
                                spacing: 6
                                Rectangle { width: 10; height: 10; radius: 5; color: root.graphColours[index % root.graphColours.length]; anchors.verticalCenter: parent.verticalCenter }
                                Label { text: root.pidName(modelData); color: "#334155"; font.bold: true }
                            }
                        }
                    }
                    Canvas {
                        id: combinedCanvas
                        property var seriesCache: Object.create(null)
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        function refreshAll() {
                            seriesCache = Object.create(null)
                            if (visible) requestPaint()
                        }
                        onVisibleChanged: if (visible) refreshAll()
                        onWidthChanged: requestPaint()
                        onHeightChanged: requestPaint()
                        onPaint: {
                            const ctx = getContext("2d")
                            ctx.reset()
                            ctx.strokeStyle = "#e2e8f0"
                            ctx.lineWidth = 1
                            for (let line = 0; line <= 5; ++line) {
                                const y = line * height / 5
                                ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke()
                            }
                            for (let seriesIndex = 0; seriesIndex < root.graphPids.length; ++seriesIndex) {
                                const pid = root.graphPids[seriesIndex]
                                if (seriesCache[pid] === undefined)
                                    seriesCache[pid] = appModel.graph_points(pid)
                                const points = seriesCache[pid]
                                if (points.length < 2) continue
                                let low = Math.min.apply(null, points)
                                let high = Math.max.apply(null, points)
                                if (high <= low) high = low + 1
                                ctx.strokeStyle = root.graphColours[seriesIndex % root.graphColours.length]
                                ctx.lineWidth = 3
                                ctx.beginPath()
                                for (let point = 0; point < points.length; ++point) {
                                    const x = point * width / Math.max(1, points.length - 1)
                                    const y = height - ((points[point] - low) / (high - low)) * height
                                    if (point === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
                                }
                                ctx.stroke()
                            }
                        }
                        Connections {
                            target: appModel
                            function onGraphSamplesChanged(pids) {
                                if (root.paused || !combinedCanvas.visible) return
                                let changed = false
                                for (const pid of pids) {
                                    if (root.graphPids.indexOf(pid) === -1) continue
                                    delete combinedCanvas.seriesCache[pid]
                                    changed = true
                                }
                                if (changed) combinedCanvas.requestPaint()
                            }
                            function onGraphHistoryCleared() { combinedCanvas.refreshAll() }
                            function onGraphSelectionChanged() { combinedCanvas.refreshAll() }
                        }
                        Connections {
                            target: root
                            function onPausedChanged() { if (!root.paused) combinedCanvas.refreshAll() }
                        }
                    }
                }
            }

            Repeater {
                model: root.graphPids
                delegate: Rectangle {
                    id: graphCard
                    required property int index
                    required property string modelData
                    property string pid: modelData
                    property color accent: root.graphColours[index % root.graphColours.length]
                    readonly property real viewportTop: graphScroll.contentItem ? (graphScroll.contentItem.contentY ?? 0) : 0
                    readonly property bool inViewport: visible && y + height > viewportTop && y < viewportTop + graphScroll.availableHeight
                    property var reading: ({value: "---", unit: ""})
                    function refresh() {
                        if (!inViewport) return
                        reading = appModel.reading_for_pid(pid)
                        graphCanvas.requestPaint()
                    }
                    onInViewportChanged: if (inViewport && !root.paused) refresh()
                    Component.onCompleted: refresh()
                    visible: !root.combinedView
                    width: visible ? Math.max(420, (graphFlow.width - graphFlow.leftPadding - graphFlow.rightPadding - graphFlow.spacing) / 2) : 0
                    height: visible ? 320 : 0
                    radius: 16
                    color: "white"
                    border.color: "#dce3ec"

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 16
                        spacing: 8

                        RowLayout {
                            Layout.fillWidth: true
                            Rectangle { width: 10; height: 10; radius: 5; color: graphCard.accent }
                            Label { text: root.pidName(graphCard.pid); font.bold: true; color: "#172033"; Layout.fillWidth: true; elide: Text.ElideRight }
                            Label {
                                text: graphCard.reading.value + (graphCard.reading.unit ? " " + graphCard.reading.unit : "")
                                font.pixelSize: 20
                                font.bold: true
                                color: "#172033"
                            }
                            Button { text: "Remove"; onClicked: root.removeGraph(index) }
                        }

                        Item {
                            Layout.fillWidth: true
                            Layout.fillHeight: true

                            Canvas {
                                id: graphCanvas
                                property bool hasSamples: false
                                anchors.fill: parent
                                onWidthChanged: if (graphCard.inViewport) requestPaint()
                                onHeightChanged: if (graphCard.inViewport) requestPaint()
                                onPaint: {
                                    const ctx = getContext("2d")
                                    ctx.reset()
                                    const points = appModel.graph_points(graphCard.pid)
                                    hasSamples = points.length >= 2
                                    ctx.strokeStyle = "#e2e8f0"
                                    ctx.lineWidth = 1
                                    for (let line = 0; line <= 5; ++line) {
                                        const y = line * height / 5
                                        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke()
                                    }
                                    if (!hasSamples) return
                                    let low = Math.min.apply(null, points)
                                    let high = Math.max.apply(null, points)
                                    if (high <= low) high = low + 1
                                    ctx.strokeStyle = graphCard.accent
                                    ctx.lineWidth = 3
                                    ctx.beginPath()
                                    for (let point = 0; point < points.length; ++point) {
                                        const x = point * width / Math.max(1, points.length - 1)
                                        const y = height - ((points[point] - low) / (high - low)) * height
                                        if (point === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
                                    }
                                    ctx.stroke()
                                    ctx.fillStyle = "#64748b"
                                    ctx.font = "12px \"" + fontProbe.font.family + "\""
                                    ctx.fillText(high.toFixed(1), 8, 16)
                                    ctx.fillText(low.toFixed(1), 8, height - 8)
                                }
                            }

                            Label {
                                anchors.centerIn: parent
                                visible: !graphCanvas.hasSamples
                                text: appModel.connected ? "Waiting for samples" : "Connect an adapter to graph live data"
                                color: "#64748b"
                            }

                            Connections {
                                target: appModel
                                function onGraphSamplesChanged(pids) {
                                    if (!root.paused && pids.indexOf(graphCard.pid) !== -1) graphCard.refresh()
                                }
                                function onGraphHistoryCleared() {
                                    graphCard.reading = ({value: "---", unit: ""})
                                    graphCanvas.hasSamples = false
                                    graphCard.refresh()
                                }
                            }
                            Connections {
                                target: root
                                function onPausedChanged() { if (!root.paused) graphCard.refresh() }
                            }
                        }
                    }
                }
            }

            Label {
                visible: root.graphPids.length === 0
                width: graphFlow.width
                height: 180
                text: "Add a PID above to create a live graph"
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
                color: "#64748b"
            }
        }
    }

    Dialog {
        id: savePresetDialog
        anchors.centerIn: Overlay.overlay
        title: "Save graph preset"
        modal: true
        standardButtons: Dialog.Cancel | Dialog.Save
        onOpened: savePresetName.text = ""
        onAccepted: appModel.save_graph_preset(savePresetName.text)
        TextField { id: savePresetName; width: 320; placeholderText: "Preset name" }
    }
    Dialog {
        id: renamePresetDialog
        anchors.centerIn: Overlay.overlay
        title: "Rename graph preset"
        modal: true
        standardButtons: Dialog.Cancel | Dialog.Save
        onAccepted: appModel.rename_graph_preset(presetName.text)
        TextField { id: presetName; width: 320; placeholderText: "Preset name" }
    }
    Dialog {
        id: deletePresetDialog
        anchors.centerIn: Overlay.overlay
        title: "Delete graph preset?"
        modal: true
        standardButtons: Dialog.Cancel | Dialog.Ok
        onAccepted: appModel.delete_graph_preset()
        Label { text: "Delete “" + appModel.currentGraphPreset + "”?" }
    }
}
