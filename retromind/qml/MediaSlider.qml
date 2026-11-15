import QtQuick
import QtQuick.Controls

Slider {
    id: control
    implicitWidth: 160
    implicitHeight: 32
    leftPadding: 6; rightPadding: 6; topPadding: 0; bottomPadding: 0
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    live: true
    background: Rectangle {
        objectName: "sliderTrack"
        x: control.leftPadding + 6
        y: (control.height - height) / 2
        width: Math.max(0, control.availableWidth - 12)
        height: 4; radius: 2
        color: control.enabled ? "#4A4A4A" : "#282828"
        Rectangle {
            objectName: "sliderFill"
            width: parent.width * control.visualPosition
            height: parent.height; radius: 2
            color: control.enabled ? "#FFFFFF" : "#606060"
        }
    }
    handle: Rectangle {
        objectName: "sliderHandle"
        x: control.leftPadding + control.visualPosition * Math.max(0, control.availableWidth - width)
        y: (control.height - height) / 2
        width: 12; height: 12; radius: 6
        color: control.enabled ? "#FFFFFF" : "#606060"
    }
    Rectangle {
        anchors.fill: parent
        radius: 5; color: "transparent"
        border.width: 1; border.color: "#FFFFFF"
        visible: control.visualFocus
    }
}
