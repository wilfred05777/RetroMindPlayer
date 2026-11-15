import QtQuick
Rectangle {
    id: art
    property var media: ({})
    property int mediaId: media.id || 0
    property string imageUrl: ""
    radius: 6; clip: true
    gradient: Gradient { GradientStop { position: 0; color: art.media.media_type === "video" ? "#293449" : "#214037" } GradientStop { position: 1; color: "#18201e" } }
    function request() { imageUrl = ""; if (mediaId > 0) controller.requestArtwork(mediaId) }
    onMediaIdChanged: request()
    Component.onCompleted: request()
    Text { anchors.centerIn: parent; text: art.media.media_type === "video" ? "\u25b6" : "\u266b"; color: "#65b890"; font.pixelSize: Math.max(18, Math.min(56, art.width * 0.32)); visible: cover.status !== Image.Ready }
    Image { id: cover; anchors.fill: parent; source: art.imageUrl; asynchronous: true; sourceSize.width: 480; sourceSize.height: 480; fillMode: Image.PreserveAspectCrop }
    Connections { target: controller; function onArtworkReady(trackId, url) { if (trackId === art.mediaId) art.imageUrl = url } }
}
