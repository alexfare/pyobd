import QtQuick
import QtQuick.Controls

Item {
    id: root
    property real gaugeValue: 0
    property real minimum: 0
    property real maximum: 100
    property int divisions: 10
    property bool showDigital: true
    property string displayValue: "---"
    property string unit: ""
    property color accent: "#2878f0"

    Canvas {
        id: dial
        anchors.fill: parent
        antialiasing: true
        onVisibleChanged: if (visible) requestPaint()
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            const ctx = getContext("2d")
            ctx.reset()
            const cx = width / 2
            const cy = height / 2
            const radius = Math.min(width, height) * 0.42
            const start = Math.PI * 0.75
            const end = Math.PI * 2.25
            ctx.lineCap = "round"
            ctx.strokeStyle = "#dce3ec"
            ctx.lineWidth = Math.max(8, radius * 0.11)
            ctx.beginPath(); ctx.arc(cx, cy, radius, start, end); ctx.stroke()
            const ratio = Math.max(0, Math.min(1, (root.gaugeValue - root.minimum) / Math.max(1, root.maximum - root.minimum)))
            ctx.strokeStyle = root.accent
            ctx.beginPath(); ctx.arc(cx, cy, radius, start, start + (end - start) * ratio); ctx.stroke()
            ctx.lineCap = "butt"
            ctx.strokeStyle = "#64748b"
            ctx.lineWidth = 1
            for (let step = 0; step <= root.divisions; ++step) {
                const tickAngle = start + (end - start) * step / root.divisions
                ctx.beginPath()
                ctx.moveTo(cx + Math.cos(tickAngle) * radius * 0.84, cy + Math.sin(tickAngle) * radius * 0.84)
                ctx.lineTo(cx + Math.cos(tickAngle) * radius * 0.97, cy + Math.sin(tickAngle) * radius * 0.97)
                ctx.stroke()
            }
            const angle = start + (end - start) * ratio
            ctx.strokeStyle = "#172033"
            ctx.lineWidth = 3
            ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx + Math.cos(angle) * radius * 0.82, cy + Math.sin(angle) * radius * 0.82); ctx.stroke()
            ctx.fillStyle = "#172033"
            ctx.beginPath(); ctx.arc(cx, cy, 6, 0, Math.PI * 2); ctx.fill()
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
            function onDivisionsChanged() { dial.requestPaint() }
            function onAccentChanged() { dial.requestPaint() }
        }
    }

    Column {
        visible: root.showDigital
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: -height * 0.45
        Label { anchors.horizontalCenter: parent.horizontalCenter; text: root.displayValue; font.pixelSize: 28; font.bold: true; color: "#172033" }
        Label { anchors.horizontalCenter: parent.horizontalCenter; text: root.unit; color: "#64748b" }
    }
}
