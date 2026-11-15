import QtQuick
import QtQuick.Controls

Menu {
    id: menu
    property real menuWidthLimit: 400
    property real menuHeightLimit: 600
    width: Math.min(300, menuWidthLimit - 16)
    height: Math.min(implicitHeight, menuHeightLimit - 16)
    padding: 6
    margins: 8
    popupType: Popup.Item
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    background: Rectangle { color: "#282828"; radius: 7; border.color: "#454545"; border.width: 1 }
}
