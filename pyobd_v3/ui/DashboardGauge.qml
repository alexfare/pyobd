import QtQuick
import QtQuick.Controls

Item {
    id: root
    property real gaugeValue: 0
    property real minimum: 0
    property real maximum: 100
    property bool showDigital: true
    property string displayValue: "---"
    property string unit: ""

    Canvas {
        id: dial
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            const cx = width / 2
            const cy = height * 0.58
            const radius = Math.min(width * 0.42, height * 0.48)
            const start = Math.PI * 0.75
            const end = Math.PI * 2.25
            ctx.lineCap = "round"
            ctx.strokeStyle = "#dce3ec"
            ctx.lineWidth = Math.max(8, radius * 0.11)
            ctx.beginPath(); ctx.arc(cx, cy, radius, start, end); ctx.stroke()
            const ratio = Math.max(0, Math.min(1, (root.gaugeValue - root.minimum) / Math.max(1, root.maximum - root.minimum)))
            ctx.strokeStyle = "#2878f0"
            ctx.beginPath(); ctx.arc(cx, cy, radius, start, start + (end - start) * ratio); ctx.stroke()
            const angle = start + (end - start) * ratio
            ctx.strokeStyle = "#172033"
            ctx.lineWidth = 3
            ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(angle) * radius * 0.82, cy + Math.sin(angle) * radius * 0.82); ctx.stroke()
            ctx.fillStyle = "#172033"
            ctx.beginPath(); ctx.arc(cx, cy, 6, 0, Math.PI * 2); ctx.fill()
            ctx.font = "11px sans-serif"
            ctx.fillStyle = "#64748b"
            ctx.fillText(root.minimum.toFixed(0), cx - radius, cy + 28)
            ctx.textAlign = "right"
            ctx.fillText(root.maximum.toFixed(0), cx + radius, cy + 28)
        }
        Connections {
            target: root
            function onGaugeValueChanged() { dial.requestPaint() }
            function onMinimumChanged() { dial.requestPaint() }
            function onMaximumChanged() { dial.requestPaint() }
        }
    }

    Column {
        visible: root.showDigital
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: height * 0.25
        Label { anchors.horizontalCenter: parent.horizontalCenter; text: root.displayValue; font.pixelSize: 28; font.bold: true; color: "#172033" }
        Label { anchors.horizontalCenter: parent.horizontalCenter; text: root.unit; color: "#64748b" }
    }
}
