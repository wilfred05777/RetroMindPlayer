import QtQuick
import QtQuick.Controls
Button {
    id: control
    property bool playbackKeyOwner: true
    property string tip: text
    property string iconName: ""
    property bool prominent: false
    property bool active: false
    implicitWidth: prominent ? 42 : 36
    implicitHeight: prominent ? 42 : 36
    padding: 0
    hoverEnabled: true; focusPolicy: Qt.StrongFocus
    Accessible.name: tip
    ToolTip.visible: hovered; ToolTip.text: tip; ToolTip.delay: 450
    contentItem: Item {
        VectorIcon {
            objectName: "buttonIcon"
            anchors.centerIn: parent
            width: control.prominent ? 24 : 20; height: width
            visible: control.iconName !== ""
            name: control.iconName
            color: !control.enabled ? "#606060" : control.prominent ? "#000000" : control.active ? "#1DB954" : "#FFFFFF"
        }
        Text {
            anchors.fill: parent; visible: control.iconName === ""
            text: control.text; font: control.font
            horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
            color: !control.enabled ? "#606060" : control.active ? "#1DB954" : "#FFFFFF"
        }
    }
    background: Rectangle {
        radius: height / 2
        color: control.prominent ? (control.down ? "#C5C5C5" : control.hovered ? "#E5E5E5" : "#FFFFFF") : (control.down ? "#383838" : control.hovered ? "#282828" : "transparent")
        Rectangle {
            objectName: "buttonFocusRing"
            anchors.fill: parent; anchors.margins: -3
            radius: height / 2; color: "transparent"
            border.width: 2; border.color: "#FFFFFF"
            visible: control.visualFocus
        }
    }
}
