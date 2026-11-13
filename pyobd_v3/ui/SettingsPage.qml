import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: root
    spacing: 0

    function sectionIndex(section) {
        const sections = ["Connection", "General", "Trace", "About"]
        return Math.max(0, sections.indexOf(section))
    }

    TabBar {
        id: settingsTabs
        Layout.fillWidth: true
        currentIndex: root.sectionIndex(appModel.settingsSection)
        Repeater {
            model: ["Connection", "General", "Trace", "About"]
            TabButton {
                required property string modelData
                text: modelData
                onClicked: appModel.open_settings(modelData)
            }
        }
    }

    StackLayout {
        Layout.fillWidth: true
        Layout.fillHeight: true
        currentIndex: settingsTabs.currentIndex

        ConnectionPage {}

        ScrollView {
            id: generalRoot
            clip: true
            contentWidth: availableWidth
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

            ColumnLayout {
                width: Math.min(generalRoot.availableWidth - 48, 820)
                anchors.horizontalCenter: parent.horizontalCenter
                spacing: 16
                Item { Layout.preferredHeight: 12 }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: performanceContent.implicitHeight + 40
                    radius: 16
                    color: "white"
                    border.color: "#dce3ec"
                    ColumnLayout {
                        id: performanceContent
                        anchors.fill: parent
                        anchors.margins: 20
                        Label { text: "Performance"; font.pixelSize: 20; font.bold: true; color: "#172033" }
                        Label { text: "Live-data polling interval"; color: "#64748b" }
                        RowLayout {
                            Layout.fillWidth: true
                            Slider { id: pollSlider; Layout.fillWidth: true; from: 30; to: 1000; stepSize: 10; value: appModel.pollInterval * 1000 }
                            Label { text: Math.round(pollSlider.value) + " ms"; Layout.preferredWidth: 70 }
                            Button { text: "Save"; onClicked: appModel.save_poll_interval(Math.round(pollSlider.value).toString()) }
                        }
                        Label { text: "The new polling interval applies on the next connection."; color: "#64748b"; font.pixelSize: 12 }
                        Label {
                            text: "Current polling: " + appModel.pollingStatus + "  ·  Vehicle worker: " + appModel.workerStatus
                            color: "#64748b"
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: maintenanceContent.implicitHeight + 40
                    radius: 16
                    color: "white"
                    border.color: "#dce3ec"
                    ColumnLayout {
                        id: maintenanceContent
                        anchors.fill: parent
                        anchors.margins: 20
                        Label { text: "Updates and logs"; font.pixelSize: 20; font.bold: true; color: "#172033" }
                        RowLayout {
                            Layout.fillWidth: true
                            Button { text: "Check for updates"; onClicked: appModel.check_for_updates() }
                            Button { text: "Open releases"; onClicked: appModel.open_app_link("releases") }
                            Item { Layout.fillWidth: true }
                            Label { text: appModel.updateStatus; color: "#64748b"; elide: Text.ElideRight; Layout.maximumWidth: 420 }
                        }
                        Label { text: "Log file"; font.bold: true }
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: appModel.logPath; color: "#64748b"; elide: Text.ElideMiddle; Layout.fillWidth: true }
                            Button { text: "Open log folder"; onClicked: appModel.open_app_link("logs") }
                        }
                        Label { text: "Recordings"; font.bold: true }
                        RowLayout {
                            Layout.fillWidth: true
                            Label { text: appModel.recordingsPath; color: "#64748b"; elide: Text.ElideMiddle; Layout.fillWidth: true }
                            Button { text: "Open recordings folder"; onClicked: appModel.open_app_link("recordings") }
                        }
                    }
                }
                Item { Layout.preferredHeight: 24 }
            }
        }

        TracePage {}
        AboutPage {}
    }
}

