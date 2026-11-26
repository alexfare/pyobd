import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    readonly property var graphPids: appModel.graphPids
    property bool paused: false
    property bool combinedView: false
    readonly property int windowSeconds: timeWindow.currentValue || 0
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

    function drawAxes(ctx, width, height, span, scale, relative, unit) {
        const plot = {left: Math.min(76, width / 3), top: 12, right: width - 10, bottom: Math.max(12, height - 26)}
        plot.width = Math.max(0, plot.right - plot.left)
        plot.height = plot.bottom - plot.top
        ctx.strokeStyle = "#e2e8f0"
        ctx.lineWidth = 1
        ctx.fillStyle = "#64748b"
        ctx.font = "12px \"" + fontProbe.font.family + "\""
        ctx.beginPath()
        for (let tick = 0; tick <= 4; ++tick) {
            const fraction = tick / 4
            const y = plot.bottom - fraction * plot.height
            const x = plot.left + fraction * plot.width
            ctx.moveTo(plot.left, y)
            ctx.lineTo(plot.right, y)
            ctx.moveTo(x, plot.top)
            ctx.lineTo(x, plot.bottom)
            if (scale) {
                ctx.textAlign = "right"
                const value = scale.low + fraction * (scale.high - scale.low)
                const suffix = relative ? "%" : unit ? " " + unit : ""
                ctx.fillText(String(Number(value.toPrecision(5))) + suffix, plot.left - 6, y + 4, plot.left - 8)
            }
            if (span > 0) {
                ctx.textAlign = tick === 0 ? "left" : tick === 4 ? "right" : "center"
                const decimals = span < 4 ? 2 : span % 4 !== 0 ? 1 : 0
                ctx.fillText(String(Number((span * fraction).toFixed(decimals))) + " s", x, plot.bottom + 18)
            }
        }
        ctx.stroke()
        ctx.strokeStyle = "#94a3b8"
        ctx.beginPath()
        ctx.moveTo(plot.left, plot.top)
        ctx.lineTo(plot.left, plot.bottom)
        ctx.lineTo(plot.right, plot.bottom)
        ctx.stroke()
        return plot
    }

    function seriesScale(samples, start) {
        let first = 0
        while (first < samples.length && samples[first][0] < start) ++first
        if (first === samples.length) return null
        let low = samples[first][1]
        let high = low
        for (let index = first + 1; index < samples.length; ++index) {
            low = Math.min(low, samples[index][1])
            high = Math.max(high, samples[index][1])
        }
        if (high === low) {
            const padding = Math.max(Math.abs(low) * 0.01, 0.5)
            low -= padding
            high += padding
        }
        return {low: low, high: high, first: first}
    }

    function drawSeries(ctx, samples, plot, start, span, scale, colour) {
        ctx.strokeStyle = colour
        ctx.fillStyle = colour
        ctx.lineWidth = 2
        ctx.beginPath()
        for (let index = scale.first; index < samples.length; ++index) {
            const sample = samples[index]
            const x = span > 0 ? plot.left + (sample[0] - start) / span * plot.width : plot.right
            const y = plot.bottom - (sample[1] - scale.low) / (scale.high - scale.low) * plot.height
            if (samples.length - scale.first === 1) {
                ctx.arc(x, y, 2.5, 0, 2 * Math.PI)
                ctx.fill()
                return
            }
            if (index === scale.first) ctx.moveTo(x, y); else ctx.lineTo(x, y)
        }
        ctx.stroke()
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
                Label { text: "Time range"; color: "#64748b" }
                ComboBox {
                    id: timeWindow
                    textRole: "label"
                    valueRole: "seconds"
                    model: [{label: "Auto", seconds: 0}, {label: "15 s", seconds: 15},
                            {label: "30 s", seconds: 30}, {label: "1 min", seconds: 60},
                            {label: "2 min", seconds: 120}]
                }
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
                    Label { text: "Relative scale per PID"; color: "#64748b" }
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
                            let start = Infinity
                            let end = -Infinity
                            for (const pid of root.graphPids) {
                                if (seriesCache[pid] === undefined)
                                    seriesCache[pid] = appModel.graph_samples(pid)
                                const samples = seriesCache[pid]
                                if (!samples.length) continue
                                start = Math.min(start, samples[0][0])
                                end = Math.max(end, samples[samples.length - 1][0])
                            }
                            const span = root.windowSeconds || Math.max(0, end - start)
                            start = Number.isFinite(end) ? end - span : 0
                            const plot = root.drawAxes(ctx, width, height, span, Number.isFinite(end) ? {low: 0, high: 100} : null, true, "")
                            for (let seriesIndex = 0; seriesIndex < root.graphPids.length; ++seriesIndex) {
                                const samples = seriesCache[root.graphPids[seriesIndex]]
                                const scale = root.seriesScale(samples, start)
                                if (!scale) continue
                                root.drawSeries(ctx, samples, plot, start, span, scale,
                                                root.graphColours[seriesIndex % root.graphColours.length])
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
                            function onWindowSecondsChanged() { if (combinedCanvas.visible) combinedCanvas.requestPaint() }
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
                        graphCanvas.samplesDirty = true
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
                                property bool samplesDirty: true
                                property var samples: []
                                anchors.fill: parent
                                onWidthChanged: if (graphCard.inViewport) requestPaint()
                                onHeightChanged: if (graphCard.inViewport) requestPaint()
                                onPaint: {
                                    const ctx = getContext("2d")
                                    ctx.reset()
                                    if (samplesDirty) {
                                        samples = appModel.graph_samples(graphCard.pid)
                                        samplesDirty = false
                                    }
                                    hasSamples = samples.length > 0
                                    const end = hasSamples ? samples[samples.length - 1][0] : 0
                                    const span = root.windowSeconds || (hasSamples ? Math.max(0, end - samples[0][0]) : 0)
                                    const start = end - span
                                    const scale = root.seriesScale(samples, start)
                                    const plot = root.drawAxes(ctx, width, height, span, scale, false, graphCard.reading.unit)
                                    if (!hasSamples) return
                                    root.drawSeries(ctx, samples, plot, start, span, scale, graphCard.accent)
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
                                    graphCanvas.samples = []
                                    graphCanvas.hasSamples = false
                                    graphCard.refresh()
                                }
                            }
                            Connections {
                                target: root
                                function onPausedChanged() { if (!root.paused) graphCard.refresh() }
                                function onWindowSecondsChanged() { if (graphCard.inViewport) graphCanvas.requestPaint() }
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
