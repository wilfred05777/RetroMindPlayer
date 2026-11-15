import QtQuick
import QtQuick.Controls
import QtQml.Models

DarkMenu {
    id: mediaActions
    required property var backend
    property int mediaId: 0
    property int playlistId: 0
    property var media: ({})
    property bool hasPlaylistMenu: false
    signal detailsRequested(int mediaId)
    function prepare() {
        media = backend.mediaInfo(mediaId)
        if (backend.userPlaylists.length > 0 && !hasPlaylistMenu) { insertMenu(2, playlistChoices); hasPlaylistMenu = true }
        else if (!backend.userPlaylists.length && hasPlaylistMenu) { removeMenu(playlistChoices); hasPlaylistMenu = false }
    }
    onAboutToShow: prepare()
    ContextAction { objectName: "mediaPlayAction"; text: "Play"; iconName: "play"; available: !!mediaActions.media.available; onTriggered: { const id = mediaActions.mediaId; mediaActions.close(); mediaActions.backend.playTrack(id) } }
    ContextAction { objectName: "mediaQueueAction"; text: "Add to queue"; iconName: "queue"; available: !!mediaActions.media.available && !mediaActions.media.queued; onTriggered: { const id = mediaActions.mediaId; mediaActions.close(); mediaActions.backend.addToQueue(id) } }
    property DarkMenu playlistChoices: DarkMenu {
        id: choices
        objectName: "playlistChoicesMenu"
        title: "Add to playlist"
        menuWidthLimit: mediaActions.menuWidthLimit
        menuHeightLimit: mediaActions.menuHeightLimit
        Instantiator {
            model: mediaActions.backend.userPlaylists
            delegate: ContextAction {
                required property var modelData
                text: modelData.name
                onTriggered: { const track = mediaActions.mediaId; const playlist = modelData.id; mediaActions.close(); mediaActions.backend.addToPlaylist(track, playlist) }
            }
            onObjectAdded: function(index, object) { choices.insertItem(index, object) }
            onObjectRemoved: function(index, object) { choices.removeItem(object) }
        }
    }
    ContextAction { objectName: "mediaFavouriteAction"; text: mediaActions.media.favourite ? "Remove from favourites" : "Add to favourites"; iconName: "heart"; onTriggered: { const id = mediaActions.mediaId; mediaActions.close(); mediaActions.backend.toggleFavourite(id) } }
    ContextAction { objectName: "mediaExplorerAction"; text: "Show in File Explorer"; iconName: "folder"; available: !!mediaActions.media.available; onTriggered: { const id = mediaActions.mediaId; mediaActions.close(); mediaActions.backend.showInExplorer(id) } }
    ContextAction { objectName: "mediaDetailsAction"; text: "Details"; iconName: "info"; onTriggered: { const id = mediaActions.mediaId; mediaActions.close(); mediaActions.detailsRequested(id) } }
    MenuSeparator {}
    ContextAction { objectName: "mediaRemovePlaylistAction"; text: "Remove from this playlist"; iconName: "remove"; available: mediaActions.playlistId > 0 && !!mediaActions.backend.playlistInfo(mediaActions.playlistId).id; destructive: true; onTriggered: { const id = mediaActions.mediaId; const playlist = mediaActions.playlistId; mediaActions.close(); mediaActions.backend.removeFromPlaylistAt(id, playlist) } }
    ContextAction { objectName: "mediaRemoveLibraryAction"; text: "Remove from library"; iconName: "trash"; destructive: true; onTriggered: { const id = mediaActions.mediaId; mediaActions.close(); mediaActions.backend.requestRemoveLibrary(id) } }
}
