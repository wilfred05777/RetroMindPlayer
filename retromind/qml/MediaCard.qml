import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Button {
    id: card
    required property var media
    implicitWidth: 166; implicitHeight: 218; hoverEnabled: true
    Accessible.name: "Play " + (media.title || "media")
    ToolTip.visible: hovered; ToolTip.text: media.title || ""
    onClicked: controller.playTrack(media.id)
    background: Rectangle { color: card.hovered ? "#282828" : "#181818"; radius: 8; border.color: card.activeFocus ? "#FFFFFF" : "transparent"; border.width: 2 }
    contentItem: ColumnLayout {
        spacing: 8
        MediaArtwork { media: card.media; Layout.fillWidth: true; Layout.preferredHeight: card.width - 24 }
        Label { text: card.media.title; color: "#FFFFFF"; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
        Label { text: (card.media.media_type === "video" ? "Video" : "Audio") + " / " + (card.media.artist || "Unknown artist"); color: "#B3B3B3"; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true }
    }
}
