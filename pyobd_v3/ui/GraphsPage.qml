import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    property string selectedPid: pidSelector.currentValue || "010C"
    property int graphRevision: 0
    spacing: 14

    RowLayout {
        Layout.fillWidth: true
        Layout.margins: 18
        Label { text: "Live PID"; font.bold: true; color: "#172033" }
        ComboBox {
            id: pidSelector
            Layout.preferredWidth: 360
            model: appModel.dashboardCatalog
            textRole: "name"
            valueRole: "pid"
            onCurrentValueChanged: graphCanvas.requestPaint()
        }
        Item { Layout.fillWidth: true }
        Label {
            property var reading: {
                root.graphRevision
                return appModel.reading_for_pid(root.selectedPid)
            }
            text: reading.value + (reading.unit ? " " + reading.unit : "")
            font.pixelSize: 24
            font.bold: true
            color: "#172033"
        }
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.fillHeight: true
        Layout.minimumHeight: 0
        Layout.margins: 18
        radius: 16
        color: "white"
        border.color: "#dce3ec"

        Canvas {
            id: graphCanvas
            anchors.fill: parent
            anchors.margins: 22
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            onPaint: {
                const ctx = getContext("2d")
                ctx.reset()
                const points = appModel.graph_points(root.selectedPid)
                ctx.strokeStyle = "#e2e8f0"
                ctx.lineWidth = 1
                for (let line = 0; line <= 5; ++line) {
                    const y = line * height / 5
                    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke()
                }
                if (points.length < 2) return
                let low = Math.min.apply(null, points)
                let high = Math.max.apply(null, points)
                if (high <= low) { high = low + 1 }
                ctx.strokeStyle = "#2878f0"
                ctx.lineWidth = 3
                ctx.beginPath()
                for (let i = 0; i < points.length; ++i) {
                    const x = i * width / Math.max(1, points.length - 1)
                    const y = height - ((points[i] - low) / (high - low)) * height
                    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
                }
                ctx.stroke()
                ctx.fillStyle = "#64748b"
                ctx.font = "12px sans-serif"
                ctx.fillText(high.toFixed(1), 8, 16)
                ctx.fillText(low.toFixed(1), 8, height - 8)
            }
        }

        Label {
            anchors.centerIn: parent
            visible: {
                root.graphRevision
                return appModel.graph_points(root.selectedPid).length < 2
            }
            text: appModel.connected ? "Waiting for samples" : "Connect an adapter to graph live data"
            color: "#64748b"
        }
    }

    Connections {
        target: appModel
        function onGraphChanged() {
            root.graphRevision++
            graphCanvas.requestPaint()
        }
    }
}
