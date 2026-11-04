import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    property var graphPids: ["010C"]
    property int graphRevision: 0
    readonly property var graphColours: ["#2878f0", "#16a34a", "#d97706", "#7e22ce", "#0891b2", "#dc2626"]
    spacing: 0

    function addGraph(pid) {
        if (!pid || graphPids.indexOf(pid) >= 0) return
        const next = graphPids.slice()
        next.push(pid)
        graphPids = next
    }

    function removeGraph(index) {
        const next = graphPids.slice()
        next.splice(index, 1)
        graphPids = next
    }

    function pidName(pid) {
        const catalog = appModel.dashboardCatalog
        for (let index = 0; index < catalog.length; ++index)
            if (catalog[index].pid === pid) return catalog[index].name
        return pid
    }

    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: 64
        color: "#f3f6fa"
        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 18
            anchors.rightMargin: 18
            Label { text: "Add live graph"; font.bold: true; color: "#172033" }
            ComboBox {
                id: pidSelector
                Layout.preferredWidth: 360
                model: appModel.dashboardCatalog
                textRole: "name"
                valueRole: "pid"
            }
            Button { text: "Add"; onClicked: root.addGraph(pidSelector.currentValue) }
            Item { Layout.fillWidth: true }
            Label { text: root.graphPids.length + (root.graphPids.length === 1 ? " graph" : " graphs"); color: "#64748b" }
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

            Repeater {
                model: root.graphPids
                delegate: Rectangle {
                    id: graphCard
                    required property int index
                    required property string modelData
                    property string pid: modelData
                    property color accent: root.graphColours[index % root.graphColours.length]
                    width: Math.max(420, (graphFlow.width - graphFlow.leftPadding - graphFlow.rightPadding - graphFlow.spacing) / 2)
                    height: 320
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
                                property var reading: {
                                    root.graphRevision
                                    return appModel.reading_for_pid(graphCard.pid)
                                }
                                text: reading.value + (reading.unit ? " " + reading.unit : "")
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
                                anchors.fill: parent
                                onWidthChanged: requestPaint()
                                onHeightChanged: requestPaint()
                                onPaint: {
                                    const ctx = getContext("2d")
                                    ctx.reset()
                                    const points = appModel.graph_points(graphCard.pid)
                                    ctx.strokeStyle = "#e2e8f0"
                                    ctx.lineWidth = 1
                                    for (let line = 0; line <= 5; ++line) {
                                        const y = line * height / 5
                                        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(width, y); ctx.stroke()
                                    }
                                    if (points.length < 2) return
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
                                    ctx.font = "12px \"" + appModel.systemFontFamily + "\""
                                    ctx.fillText(high.toFixed(1), 8, 16)
                                    ctx.fillText(low.toFixed(1), 8, height - 8)
                                }
                            }

                            Label {
                                anchors.centerIn: parent
                                visible: {
                                    root.graphRevision
                                    return appModel.graph_points(graphCard.pid).length < 2
                                }
                                text: appModel.connected ? "Waiting for samples" : "Connect an adapter to graph live data"
                                color: "#64748b"
                            }

                            Connections {
                                target: appModel
                                function onGraphChanged() { graphCanvas.requestPaint() }
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

    Connections {
        target: appModel
        function onGraphChanged() { root.graphRevision++ }
    }
}
