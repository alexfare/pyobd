import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ApplicationWindow {
    id: window
    visible: true
    width: 1440
    height: 900
    minimumWidth: 1050
    minimumHeight: 680
    title: "pyOBD v3"
    color: "#f3f6fa"

    readonly property color navy: "#122337"
    readonly property color blue: "#2878f0"
    readonly property color textPrimary: "#172033"
    readonly property color textMuted: "#64748b"
    readonly property color border: "#dce3ec"

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillHeight: true
            Layout.preferredWidth: 238
            color: window.navy

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 8

                Label {
                    text: "pyOBD"
                    color: "white"
                    font.pixelSize: 28
                    font.bold: true
                    Layout.leftMargin: 12
                    Layout.topMargin: 12
                    Layout.bottomMargin: 22
                }

                Repeater {
                    model: ["Overview", "Dashboard", "Live Data", "Graphs", "Diagnostics", "Readiness", "Vehicles"]
                    delegate: Button {
                        required property string modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: 48
                        text: modelData
                        flat: true
                        onClicked: appModel.select_page(modelData)

                        contentItem: Text {
                            text: parent.text
                            color: appModel.page === parent.text ? "white" : "#b9c7d8"
                            font.pixelSize: 15
                            font.bold: appModel.page === parent.text
                            verticalAlignment: Text.AlignVCenter
                            leftPadding: 16
                        }
                        background: Rectangle {
                            color: appModel.page === parent.text ? window.blue : "transparent"
                            radius: 10
                        }
                    }
                }

                Item { Layout.fillHeight: true }

                Label {
                    text: "pyOBD v3.0\nModern OBD-II diagnostics"
                    color: "#8fa2b8"
                    font.pixelSize: 12
                    lineHeight: 1.35
                    Layout.leftMargin: 12
                    Layout.bottomMargin: 8
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 94
                color: "white"
                border.color: window.border

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 28
                    anchors.rightMargin: 28

                    Column {
                        spacing: 3
                        Label {
                            text: appModel.page
                            color: window.textPrimary
                            font.pixelSize: 30
                            font.bold: true
                        }
                        Label {
                            text: appModel.page === "Overview"
                                  ? "Real-time vehicle data and system status"
                                  : "This screen will migrate from the v2.6 application"
                            color: window.textMuted
                            font.pixelSize: 14
                        }
                    }

                    Item { Layout.fillWidth: true }

                    Rectangle {
                        width: 126
                        height: 42
                        radius: 12
                        color: "#dcf8e8"
                        Row {
                            anchors.centerIn: parent
                            spacing: 8
                            Rectangle { width: 10; height: 10; radius: 5; color: "#22a35a" }
                            Label { text: "Demo active"; color: "#17653b"; font.bold: true }
                        }
                    }

                    Button {
                        text: "Configure"
                        Layout.preferredWidth: 120
                        Layout.preferredHeight: 42
                    }
                }
            }

            ScrollView {
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true

                ColumnLayout {
                    width: Math.max(implicitWidth, window.width - 238)
                    spacing: 14

                    GridLayout {
                        visible: appModel.page === "Overview"
                        Layout.fillWidth: true
                        Layout.margins: 24
                        columns: 4
                        columnSpacing: 14
                        rowSpacing: 14

                        Repeater {
                            model: appModel.telemetry
                            delegate: Rectangle {
                                required property var modelData
                                Layout.fillWidth: true
                                Layout.preferredHeight: 210
                                radius: 16
                                color: "white"
                                border.color: window.border

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 18
                                    spacing: 8
                                    Label {
                                        text: modelData.label
                                        color: window.textPrimary
                                        font.pixelSize: 15
                                        font.bold: true
                                    }
                                    Row {
                                        spacing: 7
                                        Label {
                                            text: modelData.value
                                            color: window.textPrimary
                                            font.pixelSize: 38
                                            font.bold: true
                                        }
                                        Label {
                                            anchors.baseline: parent.children[0].baseline
                                            text: modelData.unit
                                            color: window.textMuted
                                            font.pixelSize: 14
                                        }
                                    }
                                    Item { Layout.fillHeight: true }
                                    ProgressBar {
                                        Layout.fillWidth: true
                                        value: index === 0 ? 0.31 : index === 1 ? 0.42 : 0.72
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            Layout.preferredHeight: 310
                            radius: 16
                            color: "white"
                            border.color: window.border

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 20
                                Label {
                                    text: "Live Data Graph"
                                    color: window.textPrimary
                                    font.pixelSize: 18
                                    font.bold: true
                                }
                                Canvas {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    onPaint: {
                                        const ctx = getContext("2d")
                                        ctx.clearRect(0, 0, width, height)
                                        ctx.strokeStyle = window.blue
                                        ctx.lineWidth = 3
                                        ctx.beginPath()
                                        for (let x = 0; x <= width; x += 12) {
                                            const y = height * 0.55 + Math.sin(x / 33) * 28 + Math.sin(x / 12) * 9
                                            if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y)
                                        }
                                        ctx.stroke()
                                    }
                                }
                            }
                        }

                        Rectangle {
                            Layout.columnSpan: 2
                            Layout.fillWidth: true
                            Layout.preferredHeight: 310
                            radius: 16
                            color: "white"
                            border.color: window.border

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 20
                                spacing: 12
                                Label { text: "Vehicle Health"; color: window.textPrimary; font.pixelSize: 18; font.bold: true }
                                Label { text: "✓  No trouble codes"; color: "#18864b"; font.pixelSize: 22; font.bold: true }
                                Rectangle { Layout.fillWidth: true; height: 1; color: window.border }
                                Label { text: "I/M Readiness"; color: window.textPrimary; font.pixelSize: 15; font.bold: true }
                                Label { text: "7 of 8 monitors complete"; color: window.textMuted; font.pixelSize: 14 }
                                ProgressBar { Layout.fillWidth: true; value: 0.875 }
                                Item { Layout.fillHeight: true }
                            }
                        }
                    }

                    Label {
                        visible: appModel.page !== "Overview"
                        Layout.alignment: Qt.AlignHCenter
                        Layout.topMargin: 180
                        text: appModel.page + " migration is queued"
                        color: window.textMuted
                        font.pixelSize: 22
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 64
                color: "white"
                border.color: window.border
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 28
                    anchors.rightMargin: 28
                    spacing: 44
                    Label { text: "Protocol  Demo OBD-II"; color: window.textMuted }
                    Label { text: "Adapter  Simulated ELM327"; color: window.textMuted }
                    Label { text: "Port  DEMO"; color: window.textMuted }
                    Label { text: "VIN  DEMO0000000000001"; color: window.textMuted }
                    Item { Layout.fillWidth: true }
                    Label { text: "Voltage  14.2 V"; color: window.textPrimary; font.bold: true }
                }
            }
        }
    }
}
