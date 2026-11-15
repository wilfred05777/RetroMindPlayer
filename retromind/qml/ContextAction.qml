import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

MenuItem {
    id: action
    property string iconName: ""
    property bool destructive: false
    property bool available: true
    visible: available
    implicitHeight: available ? 36 : 0
    hoverEnabled: true
    Accessible.name: text
    contentItem: RowLayout {
        spacing: 12
        VectorIcon { name: action.iconName; color: action.enabled ? (action.destructive ? "#FF8585" : "#FFFFFF") : "#666666"; Layout.preferredWidth: 18; Layout.preferredHeight: 18; visible: action.iconName !== "" }
        Text { textFormat: Text.PlainText; text: action.text; color: action.enabled ? (action.destructive ? "#FF8585" : "#FFFFFF") : "#666666"; font: action.font; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter; Layout.fillWidth: true }
    }
    background: Rectangle { radius: 4; color: action.highlighted ? "#383838" : "transparent"; border.width: action.visualFocus ? 1 : 0; border.color: "#FFFFFF" }
}
