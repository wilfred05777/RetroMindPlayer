import QtQuick
import QtQuick.Controls

DarkMenu {
    id: playlistActions
    required property var backend
    property int playlistId: 0
    property var playlist: ({})
    signal renameRequested(int playlistId)
    onAboutToShow: playlist = backend.playlistInfo(playlistId)
    ContextAction { objectName: "playlistPlayAction"; text: "Play"; iconName: "play"; enabled: playlistActions.playlist.item_count > 0; onTriggered: { const id = playlistActions.playlistId; playlistActions.close(); playlistActions.backend.playPlaylist(id) } }
    ContextAction { objectName: "playlistRenameAction"; text: "Rename playlist"; iconName: "edit"; onTriggered: { const id = playlistActions.playlistId; playlistActions.close(); playlistActions.renameRequested(id) } }
    MenuSeparator {}
    ContextAction { objectName: "playlistDeleteAction"; text: "Delete playlist"; iconName: "trash"; destructive: true; onTriggered: { const id = playlistActions.playlistId; playlistActions.close(); playlistActions.backend.requestDeletePlaylist(id) } }
}
