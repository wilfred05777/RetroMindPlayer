import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Button {
    id: card
    property bool playbackKeyOwner: true
    required property var media
    signal contextMenuRequested(Item anchor, real x, real y)
    objectName: "mediaCard_" + media.id
    implicitWidth: 166; implicitHeight: 218; hoverEnabled: true
    Accessible.name: "Play " + (media.title || "media")
    ToolTip.visible: hovered; ToolTip.text: media.title || ""
    onClicked: controller.playTrack(media.id)
    MouseArea { anchors.fill: parent; acceptedButtons: Qt.RightButton; onClicked: function(mouse) { card.forceActiveFocus(); card.contextMenuRequested(card, mouse.x, mouse.y) } }
    IconButton { id: more; objectName: "cardMore_" + card.media.id; anchors.top: parent.top; anchors.right: parent.right; anchors.margins: 6; z: 2; iconName: "more"; tip: "Media options: " + card.media.title; onClicked: card.contextMenuRequested(more, 0, height); Keys.onReturnPressed: clicked() }
    Keys.onPressed: function(event) { if (event.key === Qt.Key_Menu || (event.key === Qt.Key_F10 && (event.modifiers & Qt.ShiftModifier))) { card.contextMenuRequested(card, 0, height); event.accepted = true } }
    background: Rectangle { color: card.hovered ? "#282828" : "#181818"; radius: 8; border.color: card.activeFocus ? "#FFFFFF" : "transparent"; border.width: 2 }
    contentItem: ColumnLayout {
        spacing: 8
        MediaArtwork { media: card.media; Layout.fillWidth: true; Layout.preferredHeight: card.width - 24 }
        Label { text: card.media.title; color: "#FFFFFF"; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
        Label { text: (card.media.media_type === "video" ? "Video" : "Audio") + " / " + (card.media.artist || "Unknown artist"); color: "#B3B3B3"; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true }
    }
}
