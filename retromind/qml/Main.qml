pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import QtMultimedia

ApplicationWindow {
    id: window
    visible: true
    width: controller.windowWidth; height: controller.windowHeight
    minimumWidth: 800; minimumHeight: 600
    title: Qt.application.displayName + " / Local music & video"; color: "#000000"
    font.family: "Segoe UI"; font.pixelSize: 14
    palette.window: "#121212"; palette.windowText: "#FFFFFF"
    palette.base: "#181818"; palette.text: "#FFFFFF"
    palette.button: "#282828"; palette.buttonText: "#FFFFFF"
    palette.placeholderText: "#B3B3B3"; palette.highlight: "#1DB954"; palette.highlightedText: "#000000"
    property int selectedTrack: -1
    property bool queueTab: false
    property bool editingPlaylist: false
    property int editingPlaylistId: 0
    property bool wasMaximized: false
    property real sideWidth: 248
    property real rightWidth: 292
    function openPlaylistMenu(playlistId, anchor, x, y) {
        if (!controller.playlistInfo(playlistId).id) return
        playlistMenu.playlistId = playlistId
        playlistMenu.popup(anchor, x, y)
    }
    function openMediaMenu(mediaId, playlistId, anchor, x, y) {
        if (!controller.mediaInfo(mediaId).id) return
        window.selectedTrack = mediaId
        mediaMenu.mediaId = mediaId
        mediaMenu.playlistId = playlistId
        mediaMenu.popup(anchor, x, y)
    }
    function editPlaylist(playlistId) {
        const playlist = controller.playlistInfo(playlistId)
        if (!playlist.id) return
        window.editingPlaylist = true
        window.editingPlaylistId = playlistId
        playlistName.text = playlist.name
        playlistError.text = ""
        playlistDialog.open()
    }
    function savePlaylistName() {
        const saved = window.editingPlaylist ? controller.renamePlaylistById(window.editingPlaylistId, playlistName.text) : controller.createPlaylist(playlistName.text)
        if (saved) { playlistDialog.close(); playlistName.clear() }
        else playlistError.text = controller.status
    }
    PlaylistMenu {
        id: playlistMenu; objectName: "playlistContextMenu"
        backend: controller; menuWidthLimit: window.width; menuHeightLimit: window.height
        onRenameRequested: function(playlistId) { window.editPlaylist(playlistId) }
    }
    MediaMenu {
        id: mediaMenu; objectName: "mediaContextMenu"
        backend: controller; menuWidthLimit: window.width; menuHeightLimit: window.height
        onDetailsRequested: function(mediaId) { mediaDetailsDialog.media = controller.mediaInfo(mediaId); mediaDetailsDialog.open() }
    }
    Dialog {
        id: confirmationDialog; objectName: "removalConfirmation"
        property var removal: ({})
        title: removal.kind === "playlist" ? "Delete playlist?" : "Remove from library?"
        anchors.centerIn: parent; modal: true; width: Math.min(window.width - 40, 520)
        closePolicy: Popup.CloseOnEscape
        contentItem: Label {
            objectName: "removalExplanation"; textFormat: Text.PlainText; wrapMode: Text.WordWrap
            text: confirmationDialog.removal.kind === "playlist" ?
                'Delete "' + (confirmationDialog.removal.title || "") + '"? Only the playlist and its entries will be deleted. Media files and library items will remain.' :
                'Remove "' + (confirmationDialog.removal.title || "") + '" from the library and all playlists? The original file will remain on disk. Importing its source folder again can re-add it.'
        }
        footer: DialogButtonBox {
            Button { id: cancelRemovalButton; text: "Cancel"; DialogButtonBox.buttonRole: DialogButtonBox.RejectRole; Keys.onReturnPressed: confirmationDialog.reject() }
            Button { objectName: "confirmRemovalButton"; text: confirmationDialog.removal.kind === "playlist" ? "Delete playlist" : "Remove from library"; DialogButtonBox.buttonRole: DialogButtonBox.AcceptRole; Keys.onReturnPressed: confirmationDialog.accept() }
            onAccepted: confirmationDialog.accept()
            onRejected: confirmationDialog.reject()
        }
        onOpened: cancelRemovalButton.forceActiveFocus()
        onAccepted: controller.confirmRemoval()
        onRejected: controller.cancelRemoval()
    }
    Dialog {
        id: mediaDetailsDialog; objectName: "mediaDetailsDialog"
        property var media: ({})
        anchors.centerIn: parent; modal: true; title: "Media details"
        width: Math.min(window.width - 40, 640); height: Math.min(window.height - 40, 450)
        standardButtons: Dialog.Close
        ScrollView {
            anchors.fill: parent
            TextArea {
                readOnly: true; selectByMouse: true; wrapMode: TextEdit.Wrap; textFormat: TextEdit.PlainText
                text: (mediaDetailsDialog.media.title || "") + "\nArtist: " + (mediaDetailsDialog.media.artist || "Unknown") +
                    "\nAlbum: " + (mediaDetailsDialog.media.album || "Unknown") + "\nType: " + (mediaDetailsDialog.media.media_type || "Unknown") +
                    "\nDuration: " + window.clock(mediaDetailsDialog.media.duration * 1000) + "\nContainer: " + (mediaDetailsDialog.media.container || "Unknown") +
                    "\nVideo codec: " + (mediaDetailsDialog.media.video_codec || "Unknown / no video") + "\nAudio codec: " + (mediaDetailsDialog.media.audio_codec || "Unknown / no audio") +
                    "\nDimensions: " + (mediaDetailsDialog.media.width ? mediaDetailsDialog.media.width + " x " + mediaDetailsDialog.media.height : "Unknown") +
                    "\nAdded: " + (mediaDetailsDialog.media.date_added || "Unknown") + "\nFile: " + (mediaDetailsDialog.media.path || "") +
                    "\nAvailable: " + (mediaDetailsDialog.media.available ? "Yes" : "No") + "\nCodec information does not guarantee playback support."
            }
        }
    }
    function focusOwnsPlaybackKey() {
        let item = window.activeFocusItem
        while (item) {
            if (item.playbackKeyOwner === true || item.checkable !== undefined) return true
            item = item.parent
        }
        return false
    }
    function clock(ms) {
        if (!ms || ms < 0) return "--:--"
        const sec = Math.floor(ms / 1000)
        return Math.floor(sec / 60) + ":" + (sec % 60).toString().padStart(2, "0")
    }
    onClosing: { controller.saveWindow(width, height); controller.savePanelWidths(sideWidth, rightWidth) }
    Component.onCompleted: { sideWidth = controller.sidebarWidth; rightWidth = controller.rightWidth }
    Shortcut { objectName: "playbackSpaceShortcut"; sequence: "Space"; enabled: !searchField.activeFocus && !playlistName.activeFocus && !window.focusOwnsPlaybackKey() && !playlistMenu.opened && !mediaMenu.opened && !confirmationDialog.opened && !playlistDialog.opened && !mediaDetailsDialog.opened; onActivated: controller.togglePlay() }
    Shortcut { sequence: "Escape"; enabled: !playlistMenu.opened && !mediaMenu.opened && !confirmationDialog.opened && !playlistDialog.opened && !mediaDetailsDialog.opened; onActivated: controller.exitFullscreen() }
    Shortcut { sequence: "Ctrl+O"; onActivated: filesDialog.open() }
    Shortcut { sequence: "Ctrl+F"; onActivated: searchField.forceActiveFocus() }
    Connections {
        target: controller
        function onChanged() {
            if (window.selectedTrack <= 0) return
            const visibleItems = controller.tracks
            for (let index = 0; index < visibleItems.length; ++index) {
                if (visibleItems[index].id === window.selectedTrack) return
            }
            window.selectedTrack = -1
        }
        function onLayoutChanged() {
            if (controller.fullscreen && window.visibility !== Window.FullScreen) { window.wasMaximized = window.visibility === Window.Maximized; window.showFullScreen() }
            else if (!controller.fullscreen && window.visibility === Window.FullScreen) { if (window.wasMaximized) window.showMaximized(); else window.showNormal() }
        }
        function onConfirmationChanged() {
            if (controller.pendingRemoval.kind) { confirmationDialog.removal = controller.pendingRemoval; confirmationDialog.open() }
            else if (confirmationDialog.opened) confirmationDialog.close()
        }
        function onClearVideo() { videoOutput.clearOutput() }
    }
    FolderImportDialog {
        id: folderDialog
        initialFolder: controller.downloadsFolder
        onScanRequested: function(folderUrl) { controller.previewFolder(folderUrl) }
        onImportRequested: controller.importDiscovered()
        previewEntries: controller.importPreview
        previewSummary: controller.importPreviewSummary
        scanning: controller.busy
        readyToImport: controller.canImportPreview
        onCancelRequested: controller.cancelImport()
    }
    FileDialog {
        id: filesDialog; objectName: "openMediaFilesDialog"; title: "Open local music and videos"; fileMode: FileDialog.OpenFiles
        nameFilters: ["Media (*.mp3 *.MP3 *.wav *.WAV *.flac *.FLAC *.ogg *.OGG *.m4a *.M4A *.mp4 *.MP4 *.m4v *.M4V *.mkv *.MKV *.webm *.WEBM *.mov *.MOV *.avi *.AVI *.wmv *.WMV *.mpg *.MPG *.mpeg *.MPEG *.ts *.TS *.m2ts *.M2TS)", "All files (*)"]
        onAccepted: controller.importFiles(selectedFiles)
    }
    Dialog {
        id: playlistDialog; objectName: "playlistNameDialog"; anchors.centerIn: parent; modal: true; width: Math.min(window.width - 40, 420)
        title: window.editingPlaylist ? "Rename playlist" : "Create playlist"
        contentItem: ColumnLayout {
            TextField { id: playlistName; objectName: "playlistNameInput"; Layout.fillWidth: true; placeholderText: "Playlist name"; maximumLength: 160; onAccepted: { if (text.trim()) window.savePlaylistName() } }
            Label { id: playlistError; textFormat: Text.PlainText; visible: text !== ""; color: "#FF8585"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
        footer: DialogButtonBox {
            standardButtons: Dialog.Ok | Dialog.Cancel
            onAccepted: window.savePlaylistName()
            onRejected: playlistDialog.reject()
            Component.onCompleted: standardButton(Dialog.Ok).enabled = Qt.binding(function() { return playlistName.text.trim().length > 0 })
        }
        onOpened: { playlistError.text = ""; playlistName.forceActiveFocus(); playlistName.selectAll() }
    }
    Dialog {
        id: detailsDialog; anchors.centerIn: parent; modal: true; title: "Diagnostics"
        width: Math.min(window.width - 60, 780); height: 420; standardButtons: Dialog.Close
        ScrollView { anchors.fill: parent; TextArea { text: controller.errorDetails || "No import or playback errors."; readOnly: true; wrapMode: TextEdit.Wrap; selectByMouse: true } }
    }
    Dialog {
        id: settingsDialog; anchors.centerIn: parent; modal: true; title: "Settings / RetroMind"
        width: Math.min(window.width - 60, 620); standardButtons: Dialog.Close
        ColumnLayout {
            width: parent.width; spacing: 14
            Label { text: "LOCAL FIRST"; color: "#1DB954"; font.bold: true }
            Label { text: "Media stays on your device. No account, streaming integration, or model download is required."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            RowLayout { Label { text: "Volume" } MediaSlider { Layout.fillWidth: true; from: 0; to: 1; value: controller.volume; onMoved: controller.setVolume(value); Accessible.name: "Settings volume" } }
            CheckBox { text: "Show library sidebar"; checked: controller.sidebar; onClicked: controller.togglePanel("sidebar") }
            CheckBox { text: "Show Now Playing / Queue panel"; checked: controller.rightPanel; onClicked: controller.togglePanel("right") }
            Label { text: controller.capabilities; color: "#B3B3B3"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Label { text: "Containers and codecs differ. Accepted extensions do not guarantee decoding or smooth 4K playback. No codec packs are installed automatically."; color: "#B3B3B3"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        }
    }
    DropArea { anchors.fill: parent; onDropped: function(drop) { if (drop.hasUrls) { controller.importFiles(drop.urls); drop.acceptProposedAction() } } }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 8; spacing: 8
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 58; spacing: 12
            Label { text: "RETROMIND"; font.bold: true; font.letterSpacing: 2; color: "#FFFFFF"; visible: window.width > 1000; leftPadding: 14; rightPadding: 12 }
            IconButton { text: "\u2630"; tip: "Toggle library sidebar"; onClicked: controller.togglePanel("sidebar") }
            IconButton { text: "\u2302"; tip: "Home"; font.pixelSize: 26; active: controller.view === "home"; onClicked: { searchField.clear(); controller.navigate("home") } }
            TextField {
                id: searchField; Layout.fillWidth: true; Layout.maximumWidth: 620; Layout.preferredHeight: 46
                placeholderText: "Search your music and videos"; leftPadding: 18; rightPadding: 18
                background: Rectangle { color: searchField.hovered ? "#282828" : "#1F1F1F"; radius: 24; border.width: searchField.activeFocus ? 2 : 0; border.color: "#FFFFFF" }
                onTextChanged: controller.search(text); Accessible.name: "Search your music and videos"
            }
            Item { Layout.fillWidth: true; visible: window.width > 1100 }
            Button { text: "+ Import"; enabled: !controller.busy; onClicked: importMenu.popup(); Menu { id: importMenu; MenuItem { text: "Open files..."; onTriggered: filesDialog.open() } MenuItem { text: "Import folder..."; onTriggered: folderDialog.selectFolder() } } }
            IconButton { text: "\u2699"; tip: "Settings"; font.pixelSize: 22; onClicked: settingsDialog.open() }
        }
        SplitView {
            Layout.fillWidth: true; Layout.fillHeight: true; orientation: Qt.Horizontal
            handle: Rectangle { implicitWidth: 8; color: SplitHandle.hovered ? "#282828" : "#000000" }
            Rectangle {
                id: librarySidebar
                SplitView.preferredWidth: controller.sidebar && window.width >= 1050 ? window.sideWidth : 64
                SplitView.minimumWidth: controller.sidebar && window.width >= 1050 ? 190 : 64
                SplitView.maximumWidth: controller.sidebar && window.width >= 1050 ? 340 : 64
                color: "#121212"; radius: 10
                onWidthChanged: if (width >= 190 && controller.sidebar && window.width >= 1050) window.sideWidth = width
                property bool expanded: width > 100
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12; spacing: 8
                    RowLayout {
                        Label { text: "Your Library"; font.bold: true; color: "#B3B3B3"; Layout.fillWidth: true; visible: librarySidebar.expanded }
                        IconButton { text: "+"; tip: "Create playlist"; font.pixelSize: 24; onClicked: { window.editingPlaylist = false; playlistName.clear(); playlistDialog.open() } }
                    }
                    Repeater {
                        model: [{name: "All media", view: "all", icon: "\u266b"}, {name: "Favourites", view: "favourites", icon: "\u2665"}, {name: "Recently added", view: "recently_added", icon: "+"}, {name: "Recently played", view: "recently_played", icon: "\u21ba"}]
                        delegate: Button {
                            required property var modelData
                            Layout.fillWidth: true; implicitHeight: 42
                            text: librarySidebar.expanded ? modelData.icon + "   " + modelData.name : modelData.icon
                            flat: true; highlighted: controller.view === modelData.view
                            Accessible.name: modelData.name; ToolTip.visible: hovered; ToolTip.text: modelData.name
                            onClicked: { window.selectedTrack = -1; controller.navigate(modelData.view) }
                            contentItem: Text { text: parent.text; color: "#FFFFFF"; verticalAlignment: Text.AlignVCenter; elide: Text.ElideRight }
                            background: Rectangle { color: parent.highlighted ? "#282828" : parent.hovered ? "#202020" : "transparent"; radius: 5; border.color: parent.activeFocus ? "#FFFFFF" : "transparent" }
                        }
                    }
                    Label { text: "PLAYLISTS"; font.pixelSize: 11; font.letterSpacing: 2; color: "#777777"; visible: librarySidebar.expanded; topPadding: 14 }
                    ListView {
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 4; model: controller.playlists
                        delegate: ItemDelegate {
                            id: savedPlaylist
                            required property var modelData
                            width: ListView.view.width; height: modelData.id === 0 ? 0 : 52; visible: modelData.id !== 0
                            text: librarySidebar.expanded ? modelData.name : "\u2261"
                            Accessible.name: modelData.name; ToolTip.visible: hovered; ToolTip.text: modelData.name
                            objectName: "sidebarPlaylist_" + modelData.id
                            contentItem: RowLayout {
                                Text { text: savedPlaylist.text; visible: librarySidebar.expanded || !playlistMore.visible; color: controller.selectedPlaylist === savedPlaylist.modelData.id ? "#1DB954" : "#FFFFFF"; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter; Layout.fillWidth: true }
                                IconButton { id: playlistMore; objectName: "playlistMore_" + savedPlaylist.modelData.id; iconName: "more"; tip: "Playlist options: " + savedPlaylist.modelData.name; visible: savedPlaylist.hovered || savedPlaylist.activeFocus || activeFocus; Layout.preferredWidth: 30; onClicked: window.openPlaylistMenu(savedPlaylist.modelData.id, playlistMore, 0, height); Keys.onReturnPressed: clicked() }
                            }
                            MouseArea { anchors.fill: parent; acceptedButtons: Qt.RightButton; onClicked: function(mouse) { savedPlaylist.forceActiveFocus(); window.openPlaylistMenu(savedPlaylist.modelData.id, savedPlaylist, mouse.x, mouse.y) } }
                            Keys.onPressed: function(event) { if (event.key === Qt.Key_Menu || (event.key === Qt.Key_F10 && (event.modifiers & Qt.ShiftModifier))) { window.openPlaylistMenu(savedPlaylist.modelData.id, savedPlaylist, 0, height); event.accepted = true } }
                            background: Rectangle { color: parent.hovered || controller.selectedPlaylist === savedPlaylist.modelData.id ? "#282828" : "transparent"; radius: 5; border.color: parent.activeFocus ? "#FFFFFF" : "transparent" }
                            onClicked: { window.selectedTrack = -1; controller.selectPlaylist(modelData.id) }
                        }
                        ScrollBar.vertical: ScrollBar {}
                    }
                    Label { text: "AUDIO + VIDEO\nStored on your device"; color: "#777777"; font.pixelSize: 11; visible: librarySidebar.expanded; lineHeight: 1.5 }
                }
            }
            Rectangle {
                id: mainPanel; SplitView.fillWidth: true; SplitView.minimumWidth: 420; color: "#121212"; radius: 10; clip: true
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 20; spacing: 14
                    Item { id: videoSlot; Layout.fillWidth: true; Layout.preferredHeight: Math.min(250, Math.max(90, mainPanel.height - 480)); visible: controller.hasVideo && controller.videoVisible && !controller.fullscreen }
                    StackLayout { Layout.fillWidth: true; Layout.fillHeight: true; currentIndex: controller.view === "home" ? 0 : 1; Loader { sourceComponent: homeContent } Loader { sourceComponent: libraryContent } }
                }
            }
            Rectangle {
                id: rightPane; visible: controller.rightPanel && window.width >= 1280
                SplitView.preferredWidth: window.rightWidth; SplitView.minimumWidth: 250; SplitView.maximumWidth: 390; color: "#121212"; radius: 10
                onWidthChanged: if (width >= 250 && visible) window.rightWidth = width
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 16; spacing: 16
                    RowLayout {
                        Button { text: "Now Playing"; flat: true; highlighted: !window.queueTab; onClicked: window.queueTab = false }
                        Button { text: "Queue"; flat: true; highlighted: window.queueTab; onClicked: window.queueTab = true }
                        Item { Layout.fillWidth: true }
                        IconButton { text: "\u00d7"; tip: "Close side panel"; onClicked: controller.togglePanel("right") }
                    }
                    StackLayout { Layout.fillWidth: true; Layout.fillHeight: true; currentIndex: window.queueTab ? 1 : 0; Loader { sourceComponent: nowContent } Loader { sourceComponent: queueContent } }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.preferredHeight: 20
            Label { text: controller.status; color: "#B3B3B3"; elide: Text.ElideRight; font.pixelSize: 11; Layout.fillWidth: true; ToolTip.visible: statusMouse.containsMouse; ToolTip.text: text; MouseArea { id: statusMouse; anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton } }
            ProgressBar { visible: controller.busy; Layout.preferredWidth: 130; value: controller.importProgress; indeterminate: controller.importProgress === 0 }
            Button { text: "Cancel"; visible: controller.busy; flat: true; implicitHeight: 22; onClicked: controller.cancelImport() }
            Button { text: "Details"; flat: true; implicitHeight: 22; font.pixelSize: 11; onClicked: detailsDialog.open() }
        }
        Item { Layout.preferredHeight: 112; Layout.fillWidth: true }
    }
    Rectangle {
        id: fullscreenStage
        anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: playerBar.top
        visible: controller.fullscreen; color: "#000000"; z: 90
    }
    Rectangle {
        id: videoContainer; parent: controller.fullscreen ? fullscreenStage : videoSlot
        anchors.fill: parent; visible: controller.hasVideo && (controller.videoVisible || controller.fullscreen)
        color: "#000000"; radius: 6; clip: true
        VideoOutput {
            id: videoOutput; objectName: "mainVideoOutput"; anchors.fill: parent
            fillMode: VideoOutput.PreserveAspectFit; endOfStreamPolicy: VideoOutput.ClearOutput
            Component.onCompleted: controller.attachVideo(videoSink)
        }
        MouseArea { anchors.fill: parent; onDoubleClicked: controller.toggleFullscreen() }
        RowLayout {
            anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.margins: 12
            Label { text: controller.currentTitle; color: "#FFFFFF"; Layout.fillWidth: true; elide: Text.ElideRight; style: Text.Outline; styleColor: "#000000" }
            IconButton { iconName: controller.fullscreen ? "exit-fullscreen" : "fullscreen"; tip: controller.fullscreen ? "Exit fullscreen (Escape)" : "Fullscreen video"; onClicked: controller.toggleFullscreen() }
        }
    }
    Rectangle {
        id: playerBar; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
        height: 120; color: "#000000"; z: 100
        Rectangle { anchors.top: parent.top; width: parent.width; height: 1; color: "#202020" }
        RowLayout {
            anchors.fill: parent; anchors.margins: 14; spacing: 14
            RowLayout {
                Layout.preferredWidth: window.width < 1100 ? 180 : 270
                MediaArtwork { Layout.preferredWidth: 52; Layout.preferredHeight: 52; media: controller.currentTrack }
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 4
                    Label { text: controller.currentTitle; font.bold: true; color: "#FFFFFF"; elide: Text.ElideRight; Layout.fillWidth: true }
                    Label { text: controller.currentArtist; color: "#B3B3B3"; font.pixelSize: 11; elide: Text.ElideRight; Layout.fillWidth: true }
                }
                IconButton { iconName: "heart"; tip: "Favourite current media"; active: !!controller.currentTrack.favourite; enabled: !!controller.currentTrack.id; onClicked: controller.toggleFavourite(controller.currentTrack.id) }
            }
            ColumnLayout {
                Layout.fillWidth: true; spacing: 5
                RowLayout {
                    Layout.alignment: Qt.AlignHCenter; spacing: 9
                    IconButton { iconName: "shuffle"; tip: "Shuffle " + (controller.shuffle ? "on" : "off"); active: controller.shuffle; onClicked: controller.toggleShuffle() }
                    IconButton { iconName: "previous"; tip: "Previous"; onClicked: controller.step(-1) }
                    IconButton {
                        objectName: "playPauseButton"
                        iconName: controller.playing ? "pause" : "play"
                        prominent: true
                        tip: controller.playing ? "Pause" : "Play"
                        onClicked: controller.togglePlay()
                    }
                    IconButton { iconName: "stop"; tip: "Stop"; onClicked: controller.stop() }
                    IconButton { iconName: "next"; tip: "Next"; onClicked: controller.step(1) }
                    IconButton { iconName: controller.repeat === "one" ? "repeat-one" : "repeat"; tip: "Repeat: " + controller.repeat; active: controller.repeat !== "off"; onClicked: controller.cycleRepeat() }
                }
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: controller.position ? window.clock(controller.position) : "0:00"; color: "#B3B3B3"; font.pixelSize: 11; Layout.preferredWidth: 38; horizontalAlignment: Text.AlignRight }
                    MediaSlider { objectName: "seekSlider"; Layout.fillWidth: true; enabled: controller.duration > 0; from: 0; to: Math.max(1, controller.duration); value: controller.position; onMoved: controller.seek(value); Accessible.name: enabled ? "Seek position" : "Seek unavailable: duration unknown"; ToolTip.visible: hovered && !enabled; ToolTip.text: "Seeking unavailable: duration unknown" }
                    Label { text: window.clock(controller.duration); color: "#B3B3B3"; font.pixelSize: 11; Layout.preferredWidth: 40 }
                }
            }
            RowLayout {
                Layout.preferredWidth: window.width < 1100 ? 240 : 270; spacing: 2
                IconButton { iconName: controller.muted ? "mute" : "volume"; tip: controller.muted ? "Unmute" : "Mute"; active: controller.muted; onClicked: controller.toggleMute() }
                MediaSlider { objectName: "volumeSlider"; Layout.fillWidth: true; Layout.minimumWidth: 52; from: 0; to: 1; value: controller.volume; onMoved: controller.setVolume(value); Accessible.name: "Volume" }
                IconButton { iconName: "queue"; tip: "Show queue"; active: window.queueTab && controller.rightPanel; onClicked: { window.queueTab = true; if (window.width < 1280) queueDialog.open(); else if (!controller.rightPanel) controller.togglePanel("right") } }
                IconButton { iconName: "video"; tip: "Toggle video panel"; enabled: controller.hasVideo; active: controller.videoVisible; onClicked: controller.togglePanel("video") }
                IconButton { iconName: controller.fullscreen ? "exit-fullscreen" : "fullscreen"; tip: "Toggle fullscreen video"; enabled: controller.hasVideo; onClicked: controller.toggleFullscreen() }
            }
        }
    }
    Dialog {
        id: queueDialog; anchors.centerIn: parent; modal: true; title: "Up next"; width: 430; height: 450; standardButtons: Dialog.Close
        Loader { anchors.fill: parent; sourceComponent: queueContent }
    }
    Component {
        id: nowContent
        ScrollView {
            contentWidth: availableWidth
            ColumnLayout {
                width: parent.width; spacing: 16
                MediaArtwork { Layout.fillWidth: true; Layout.preferredHeight: width; media: controller.currentTrack }
                RowLayout {
                    Layout.fillWidth: true
                    Label { text: controller.currentTitle; color: "#FFFFFF"; font.pixelSize: 23; font.bold: true; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                    IconButton { iconName: "heart"; tip: "Favourite current media"; enabled: !!controller.currentTrack.id; active: !!controller.currentTrack.favourite; onClicked: controller.toggleFavourite(controller.currentTrack.id) }
                }
                Label { text: controller.currentArtist; color: "#B3B3B3"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Label { text: controller.currentTrack.album || "Album unknown"; color: "#B3B3B3"; visible: !!controller.currentTrack.id; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Rectangle {
                    Layout.fillWidth: true; implicitHeight: detailsLabel.implicitHeight + 28; color: "#181818"; radius: 8
                    Label {
                        id: detailsLabel; anchors.fill: parent; anchors.margins: 14; wrapMode: Text.WordWrap; color: "#B3B3B3"; lineHeight: 1.5
                        text: !controller.currentTrack.id ? "Pick something from your local collection, or import media to begin." :
                            "MEDIA DETAILS\n" + (controller.currentTrack.media_type || "Unknown") + " / " + (controller.currentTrack.container || "Container unknown") +
                            "\nVideo: " + (controller.currentTrack.video_codec || "Unknown / no video") + "\nAudio: " + (controller.currentTrack.audio_codec || "Unknown / no audio") +
                            (controller.currentTrack.width ? "\n" + controller.currentTrack.width + " x " + controller.currentTrack.height : "")
                    }
                }
                Label { text: "LOCAL PLAYBACK / RETROMIND"; color: "#777777"; font.pixelSize: 10; font.letterSpacing: 1; Layout.fillWidth: true; wrapMode: Text.WordWrap }
            }
        }
    }
    Component {
        id: queueContent
        ListView {
            clip: true; spacing: 6; model: controller.queueTracks
            delegate: Rectangle {
                required property var modelData
                width: ListView.view.width; height: 68; color: "#181818"; radius: 6
                RowLayout {
                    anchors.fill: parent; anchors.margins: 6
                    MediaArtwork { media: modelData; Layout.preferredWidth: 42; Layout.preferredHeight: 42 }
                    Button { text: modelData.title; flat: true; Layout.fillWidth: true; onClicked: controller.playQueued(modelData.id); Accessible.name: "Play queued " + modelData.title; contentItem: Text { text: parent.text; color: "#FFFFFF"; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter } }
                    IconButton { text: "\u00d7"; tip: "Remove from queue"; onClicked: controller.removeQueued(modelData.id) }
                }
            }
            Label { anchors.centerIn: parent; width: parent.width - 20; visible: parent.count === 0; text: "Your queue is clear.\nPlay a library item to queue its view."; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; color: "#B3B3B3" }
            ScrollBar.vertical: ScrollBar {}
        }
    }
    Component {
        id: homeContent
        ScrollView {
            contentWidth: availableWidth
            ColumnLayout {
                width: parent.width; spacing: 20
                Label { text: "YOUR COLLECTION, IN FOCUS"; color: "#1DB954"; font.pixelSize: 11; font.letterSpacing: 2 }
                Label { text: "Made for your moments"; font.pixelSize: 34; font.bold: true; color: "#FFFFFF"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Label { text: "Music and moving pictures. All yours. All local."; color: "#B3B3B3"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                Rectangle {
                    visible: !controller.recentAdded.length; Layout.fillWidth: true; Layout.preferredHeight: 180; radius: 10; color: "#181818"
                    ColumnLayout {
                        anchors.centerIn: parent; width: parent.width - 40
                        Label { text: "Start with something you love"; font.pixelSize: 24; font.bold: true; color: "#FFFFFF"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        Label { text: "Import your music and videos, or drop local files into this window."; color: "#B3B3B3"; Layout.fillWidth: true; wrapMode: Text.WordWrap }
                        Button { text: "Import folder"; onClicked: folderDialog.selectFolder() }
                    }
                }
                Label { text: "Continue listening / watching"; font.pixelSize: 22; font.bold: true; color: "#FFFFFF"; visible: !!controller.continueTrack.id }
                Button {
                    visible: !!controller.continueTrack.id; Layout.fillWidth: true; implicitHeight: 82; onClicked: controller.resumeLast()
                    background: Rectangle { color: parent.hovered ? "#283b31" : "#1b2b23"; radius: 8; border.color: parent.activeFocus ? "#FFFFFF" : "transparent" }
                    contentItem: RowLayout {
                        MediaArtwork { media: controller.continueTrack; Layout.preferredWidth: 60; Layout.preferredHeight: 60 }
                        Label { text: controller.continueTrack.title || ""; font.bold: true; color: "#FFFFFF"; elide: Text.ElideRight; Layout.fillWidth: true }
                        Label { text: "Resume  \u25b6"; color: "#1DB954" }
                    }
                }
                Repeater {
                    model: ["Recently added", "Recently played"]
                    delegate: ColumnLayout {
                        required property string modelData
                        required property int index
                        property var items: index === 0 ? controller.recentAdded : controller.recentPlayed
                        Layout.fillWidth: true; spacing: 12; visible: items.length > 0
                        RowLayout {
                            Label { text: modelData; color: "#FFFFFF"; font.bold: true; font.pixelSize: 22; Layout.fillWidth: true }
                            Button { text: "Show all"; flat: true; onClicked: controller.navigate(index === 0 ? "recently_added" : "recently_played") }
                        }
                        ListView {
                            Layout.fillWidth: true; Layout.preferredHeight: 230; orientation: ListView.Horizontal; spacing: 14; clip: true; model: parent.items
                            delegate: MediaCard { required property var modelData; media: modelData; onContextMenuRequested: function(anchor, x, y) { window.openMediaMenu(modelData.id, 0, anchor, x, y) } }
                            ScrollBar.horizontal: ScrollBar {}
                        }
                    }
                }
                Label { text: "Your playlists"; font.pixelSize: 22; font.bold: true; color: "#FFFFFF"; visible: controller.playlists.length > 1 }
                Flow {
                    Layout.fillWidth: true; spacing: 12
                    Repeater {
                        model: controller.playlists
                        delegate: Button {
                            required property var modelData
                            visible: modelData.id > 0; width: visible ? 180 : 0; height: visible ? 84 : 0
                            text: modelData.name; onClicked: controller.selectPlaylist(modelData.id)
                            background: Rectangle { color: parent.hovered ? "#282828" : "#181818"; radius: 8; border.color: parent.activeFocus ? "#FFFFFF" : "transparent" }
                            contentItem: Text { text: "\u2261  " + parent.text; color: "#FFFFFF"; elide: Text.ElideRight; verticalAlignment: Text.AlignVCenter; font.bold: true }
                        }
                    }
                }
            }
        }
    }
    Component {
        id: libraryContent
        ColumnLayout {
            spacing: 12
            RowLayout {
                Layout.fillWidth: true
                ColumnLayout {
                    Layout.fillWidth: true
                    Label { text: controller.selectedPlaylist ? "PLAYLIST" : "YOUR LIBRARY"; visible: mainPanel.height >= 560; color: "#1DB954"; font.pixelSize: 11; font.letterSpacing: 2 }
                    Label { text: controller.viewTitle; color: "#FFFFFF"; font.pixelSize: mainPanel.width < 600 || mainPanel.height < 560 ? 26 : 36; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                    Label { text: controller.tracks.length + " items / " + (controller.totalDuration ? window.clock(controller.totalDuration * 1000) + " known duration" : "Duration unknown"); color: "#B3B3B3"; font.pixelSize: 12 }
                }
                IconButton { objectName: "playlistHeadingMenu"; iconName: "more"; tip: "Playlist options"; visible: controller.selectedPlaylist > 0; onClicked: window.openPlaylistMenu(controller.selectedPlaylist, this, 0, height); Keys.onReturnPressed: clicked() }
            }
            RowLayout {
                Button { text: "\u25b6 Play"; enabled: controller.tracks.length > 0; onClicked: controller.playView() }
                IconButton { iconName: "shuffle"; tip: "Toggle shuffle"; active: controller.shuffle; onClicked: controller.toggleShuffle() }
                Item { Layout.fillWidth: true }
                ComboBox { Layout.preferredWidth: mainPanel.width < 600 ? 120 : 160; model: ["Title / order", "Artist", "Date added", "Duration"]; currentIndex: ["title", "artist", "date_added", "duration"].indexOf(controller.sortOrder); onActivated: controller.setSort(["title", "artist", "date_added", "duration"][currentIndex]); Accessible.name: "Sort media" }
                IconButton { text: controller.grid ? "\u2261" : "\u25a6"; tip: controller.grid ? "List view" : "Grid view"; onClicked: controller.togglePanel("grid") }
            }
            RowLayout {
                Repeater { model: ["All", "Audio", "Video"]; delegate: Button { required property string modelData; text: modelData; flat: true; highlighted: controller.mediaFilter === modelData.toLowerCase(); onClicked: controller.setMediaFilter(modelData.toLowerCase()); Accessible.name: modelData + " media filter" } }
                Item { Layout.fillWidth: true }
            }
            StackLayout { Layout.fillWidth: true; Layout.fillHeight: true; Layout.minimumHeight: 66; currentIndex: controller.grid ? 1 : 0; Loader { sourceComponent: listContent } Loader { sourceComponent: gridContent } }
            Flow {
                Layout.fillWidth: true; spacing: 6
                ComboBox { id: playlistTarget; width: Math.max(130, Math.min(200, mainPanel.width - 290)); model: controller.playlists; textRole: "name"; valueRole: "id"; Accessible.name: "Destination playlist" }
                Button { text: "Add selected"; enabled: window.selectedTrack > 0; onClicked: controller.addToPlaylist(window.selectedTrack, playlistTarget.currentValue) }
                Button { text: "Remove"; visible: controller.selectedPlaylist > 0; enabled: window.selectedTrack > 0; onClicked: controller.removeFromPlaylist(window.selectedTrack) }
                IconButton { text: "\u2191"; tip: "Move selected up"; visible: controller.selectedPlaylist > 0; enabled: window.selectedTrack > 0; onClicked: controller.moveTrack(window.selectedTrack, -1) }
                IconButton { text: "\u2193"; tip: "Move selected down"; visible: controller.selectedPlaylist > 0; enabled: window.selectedTrack > 0; onClicked: controller.moveTrack(window.selectedTrack, 1) }
            }
        }
    }
    Component {
        id: listContent
        ListView {
            id: mediaList; objectName: "libraryList"; clip: true; spacing: 3; model: controller.tracks
            delegate: Rectangle {
                id: mediaRow
                required property var modelData
                required property int index
                objectName: "mediaRow_" + modelData.id
                width: mediaList.width; height: 66; radius: 5
                color: window.selectedTrack === modelData.id ? "#303030" : rowHover.hovered ? "#242424" : "transparent"
                border.color: activeFocus ? "#FFFFFF" : "transparent"; activeFocusOnTab: true
                Keys.onReturnPressed: controller.playTrack(modelData.id)
                HoverHandler { id: rowHover }
                MouseArea { anchors.fill: parent; acceptedButtons: Qt.RightButton; onClicked: function(mouse) { mediaRow.forceActiveFocus(); window.openMediaMenu(mediaRow.modelData.id, controller.selectedPlaylist, mediaRow, mouse.x, mouse.y) } }
                Keys.onPressed: function(event) { if (event.key === Qt.Key_Menu || (event.key === Qt.Key_F10 && (event.modifiers & Qt.ShiftModifier))) { window.openMediaMenu(mediaRow.modelData.id, controller.selectedPlaylist, mediaRow, 0, height); event.accepted = true } }
                TapHandler { acceptedButtons: Qt.LeftButton; onTapped: { window.selectedTrack = modelData.id; parent.forceActiveFocus() } onDoubleTapped: controller.playTrack(modelData.id) }
                RowLayout {
                    anchors.fill: parent; anchors.margins: 7; spacing: 10
                    Label { text: controller.currentTrack.id === modelData.id ? "\u25b6" : String(index + 1); color: controller.currentTrack.id === modelData.id ? "#1DB954" : "#777777"; Layout.preferredWidth: 20 }
                    MediaArtwork { media: modelData; Layout.preferredWidth: 46; Layout.preferredHeight: 46 }
                    ColumnLayout {
                        Layout.fillWidth: true; spacing: 4
                        Label { text: modelData.title; color: controller.currentTrack.id === modelData.id ? "#1DB954" : "#FFFFFF"; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                        Label { text: (modelData.artist || "Unknown artist") + (modelData.album ? " / " + modelData.album : ""); color: "#B3B3B3"; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                    }
                    Label { text: modelData.media_type === "video" ? "VIDEO" : "AUDIO"; color: "#B3B3B3"; font.pixelSize: 10 }
                    IconButton { text: modelData.favourite ? "\u2665" : "\u2661"; tip: "Toggle favourite"; active: !!modelData.favourite; onClicked: controller.toggleFavourite(modelData.id) }
                    Label { text: window.clock(modelData.duration * 1000); color: "#B3B3B3"; Layout.preferredWidth: 42; horizontalAlignment: Text.AlignRight; font.pixelSize: 12 }
                    IconButton { iconName: "play"; tip: "Play " + modelData.title; onClicked: controller.playTrack(modelData.id) }
                    IconButton { objectName: "mediaMore_" + modelData.id; iconName: "more"; tip: "Media options: " + modelData.title; onClicked: window.openMediaMenu(modelData.id, controller.selectedPlaylist, this, 0, height); Keys.onReturnPressed: clicked() }
                }
            }
            Label { anchors.centerIn: parent; width: parent.width - 30; visible: mediaList.count === 0; text: "No media here yet.\nImport local files or adjust your search and filters."; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; color: "#B3B3B3"; lineHeight: 1.5 }
            ScrollBar.vertical: ScrollBar {}
        }
    }
    Component {
        id: gridContent
        GridView {
            id: mediaGrid; model: controller.tracks; clip: true
            cellWidth: width / Math.max(2, Math.floor(width / 180)); cellHeight: cellWidth + 68
            delegate: ColumnLayout {
                required property var modelData
                width: mediaGrid.cellWidth - 12; height: mediaGrid.cellHeight - 12; spacing: 0
                MediaCard { media: modelData; Layout.fillWidth: true; Layout.fillHeight: true; onContextMenuRequested: function(anchor, x, y) { window.openMediaMenu(modelData.id, controller.selectedPlaylist, anchor, x, y) } }
                Button { text: window.selectedTrack === modelData.id ? "Selected" : "Select"; Layout.fillWidth: true; flat: true; onClicked: window.selectedTrack = modelData.id }
            }
            Label { anchors.centerIn: parent; width: parent.width - 30; visible: mediaGrid.count === 0; text: "No matching media. Import files or adjust your filters."; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; color: "#B3B3B3" }
            ScrollBar.vertical: ScrollBar {}
        }
    }
}
