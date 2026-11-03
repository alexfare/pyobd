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
                    model: ["Overview", "Dashboard", "Live Data", "Graphs", "Diagnostics", "Readiness", "Freeze Frame", "Vehicles", "Connection"]
                    delegate: Button {
                        required property string modelData
                        Layout.fillWidth: true
                        Layout.preferredHeight: 44
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
                Layout.preferredHeight: 86
                Layout.minimumHeight: 86
                color: "white"
                border.color: window.border
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 28
                    anchors.rightMargin: 28
                    Column {
                        spacing: 3
                        Label { text: appModel.page; color: window.textPrimary; font.pixelSize: 28; font.bold: true }
                        Label { text: "Vehicle diagnostics and live data"; color: window.textMuted; font.pixelSize: 14 }
                    }
                    Item { Layout.fillWidth: true }
                    Rectangle {
                        width: 132
                        height: 40
                        radius: 12
                        color: appModel.connected ? "#dcf8e8" : "#fee2e2"
                        Row {
                            anchors.centerIn: parent
                            spacing: 8
                            Rectangle { width: 10; height: 10; radius: 5; color: appModel.connected ? "#22a35a" : "#ef4444" }
                            Label { text: appModel.connectionStatus; color: appModel.connected ? "#17653b" : "#991b1b"; font.bold: true }
                        }
                    }
                    Button { text: "Configure"; onClicked: appModel.select_page("Connection") }
                }
            }

            Loader {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 0
                sourceComponent: {
                    if (appModel.page === "Overview") return overviewPage
                    if (appModel.page === "Dashboard") return dashboardPage
                    if (appModel.page === "Graphs") return graphsPage
                    if (appModel.page === "Connection") return connectionPage
                    if (appModel.page === "Live Data") return liveDataPage
                    if (appModel.page === "Diagnostics") return diagnosticsPage
                    if (appModel.page === "Readiness") return readinessPage
                    if (appModel.page === "Freeze Frame") return freezeFramePage
                    if (appModel.page === "Vehicles") return vehiclesPage
                    return placeholderPage
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 58
                Layout.minimumHeight: 58
                color: "white"
                border.color: window.border
                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: 28
                    anchors.rightMargin: 28
                    spacing: 36
                    Label { text: "Protocol  " + appModel.protocol; color: window.textMuted }
                    Label { text: "Adapter  " + appModel.adapter; color: window.textMuted }
                    Label { text: "Port  " + appModel.port; color: window.textMuted; elide: Text.ElideMiddle; Layout.maximumWidth: 260 }
                    Label { text: "VIN  " + appModel.vin; color: window.textMuted }
                    Item { Layout.fillWidth: true }
                    Label { text: "Voltage  " + appModel.voltage; color: window.textPrimary; font.bold: true }
                }
            }
        }
    }

    Component { id: overviewPage; OverviewPage {} }
    Component { id: dashboardPage; DashboardPage {} }
    Component { id: graphsPage; GraphsPage {} }
    Component { id: connectionPage; ConnectionPage {} }
    Component { id: liveDataPage; LiveDataPage {} }
    Component { id: diagnosticsPage; DiagnosticsPage {} }
    Component { id: readinessPage; ReadinessPage {} }
    Component { id: freezeFramePage; FreezeFramePage {} }
    Component { id: vehiclesPage; VehiclesPage {} }
    Component {
        id: placeholderPage
        Item {
            Label {
                anchors.centerIn: parent
                text: appModel.page + " migration is queued for Phase 3"
                color: "#64748b"
                font.pixelSize: 22
            }
        }
    }
}
