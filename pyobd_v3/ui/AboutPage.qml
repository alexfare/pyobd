import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ScrollView {
    id: root
    clip: true
    contentWidth: availableWidth
    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

    ColumnLayout {
        width: Math.min(root.availableWidth - 48, 820)
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 14
        Item { Layout.preferredHeight: 18 }
        Label { text: "pyOBD"; font.pixelSize: 34; font.bold: true; color: "#172033" }
        Label { text: "Version " + appModel.appVersion + "  ·  Qt Desktop"; color: "#64748b" }
        Label {
            Layout.fillWidth: true
            text: "Open-source OBD-II diagnostics for live vehicle data, customizable dashboards, graphs, readiness monitors, freeze-frame data, and diagnostic trouble codes."
            wrapMode: Text.Wrap
            color: "#172033"
        }
        Label { text: "Project"; font.pixelSize: 20; font.bold: true; Layout.topMargin: 12 }
        RowLayout {
            Button { text: "Source code"; onClicked: appModel.open_app_link("project") }
            Button { text: "Releases"; onClicked: appModel.open_app_link("releases") }
            Button { text: "Report an issue"; onClicked: appModel.open_app_link("issues") }
            Button { text: "Support"; onClicked: appModel.open_app_link("support") }
        }
        Label { text: "Credits"; font.pixelSize: 20; font.bold: true; Layout.topMargin: 12 }
        Label {
            Layout.fillWidth: true
            text: "Maintained by FareBrothers, LLC\nBased on work by Jure Poljsak, SeCons Ltd., and Charles Donour Sizemore"
            wrapMode: Text.Wrap
            color: "#172033"
        }
        Label { text: "Open-source license"; font.pixelSize: 20; font.bold: true; Layout.topMargin: 12 }
        Label {
            Layout.fillWidth: true
            text: "pyOBD is licensed under GNU GPL-2.0. You may redistribute and modify it under that license. It comes with absolutely no warranty."
            wrapMode: Text.Wrap
            color: "#172033"
        }
        Button { text: "View GNU GPL-2.0 license"; onClicked: appModel.open_app_link("license") }
        Item { Layout.preferredHeight: 24 }
    }
}

