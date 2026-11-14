pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

ApplicationWindow {
    id: window
    visible: true
    width: 1100; height: 760
    minimumWidth: 860; minimumHeight: 620
    title: "RetroMind Player"
    color: "#121619"
    palette.window: "#20272c"
    palette.windowText: "#e0e7e9"
    palette.base: "#111719"
    palette.text: "#e0e7e9"
    palette.button: "#354047"
    palette.buttonText: "#e0e7e9"
    palette.highlight: "#72e98b"
    palette.highlightedText: "#101b13"
    font.family: "Segoe UI"
    font.pixelSize: 14
    property int selectedTrack: -1
    function clock(ms) {
        let seconds = Math.floor(ms / 1000)
        return Math.floor(seconds / 60) + ":" + (seconds % 60).toString().padStart(2, "0")
    }
    FolderDialog {
        id: folderDialog
        title: "Import a music folder (including subfolders)"
        onAccepted: controller.importFolder(selectedFolder.toString())
    }
    Dialog {
        id: detailsDialog
        title: "Import details"
        anchors.centerIn: parent
        width: Math.min(window.width - 80, 760); height: 400
        modal: true
        standardButtons: Dialog.Close
        ScrollView {
            anchors.fill: parent
            TextArea { text: controller.errorDetails || "No import errors."; readOnly: true; wrapMode: TextEdit.Wrap; selectByMouse: true }
        }
    }
    ColumnLayout {
        anchors.fill: parent; anchors.margins: 18; spacing: 12
        RowLayout {
            Label { text: "RETROMIND"; font.pixelSize: 24; font.bold: true; font.letterSpacing: 3; color: "#9ef7ad" }
            Label { text: "LOCAL AUDIO / 01"; color: "#91a1aa"; Layout.fillWidth: true }
            Button { text: "Import folder"; enabled: !controller.busy; onClicked: folderDialog.open() }
            Button { text: "Cancel import"; visible: controller.busy; onClicked: controller.cancelImport() }
        }
        Rectangle {
            Layout.fillWidth: true; Layout.preferredHeight: 186
            radius: 5; border.color: "#536068"
            gradient: Gradient { GradientStop { position: 0; color: "#343e45" } GradientStop { position: 1; color: "#20272d" } }
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 14; spacing: 8
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true; color: "#0b1912"; border.color: "#425b49"; radius: 3
                    RowLayout {
                        anchors.fill: parent; anchors.margins: 12
                        ColumnLayout {
                            Layout.fillWidth: true
                            Label { text: controller.currentTitle; color: "#9dffac"; font.pixelSize: 22; font.bold: true; elide: Text.ElideRight; Layout.fillWidth: true }
                            Label { text: controller.currentArtist; color: "#79be88"; elide: Text.ElideRight; Layout.fillWidth: true }
                        }
                        Label { text: clock(controller.position) + " / " + clock(controller.duration); color: "#9dffac"; font.family: "Consolas"; font.pixelSize: 22 }
                    }
                }
                Slider {
                    id: seekSlider
                    Layout.fillWidth: true; from: 0; to: Math.max(1, controller.duration)
                    value: controller.position
                    onMoved: controller.seek(value)
                    Accessible.name: "Seek position"
                }
                RowLayout {
                    Button { text: "Previous"; onClicked: controller.step(-1) }
                    Button { text: controller.playing ? "Pause" : "Play"; highlighted: true; onClicked: controller.togglePlay() }
                    Button { text: "Stop"; onClicked: controller.stop() }
                    Button { text: "Next"; onClicked: controller.step(1) }
                    Item { Layout.fillWidth: true }
                    Label { text: "VOL " + Math.round(controller.volume * 100) + "%"; color: "#b7c8cf" }
                    Slider { Layout.preferredWidth: 160; from: 0; to: 1; value: controller.volume; onMoved: controller.setVolume(value); Accessible.name: "Volume" }
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true; Layout.fillHeight: true; spacing: 12
            Rectangle {
                Layout.preferredWidth: 220; Layout.fillHeight: true; color: "#20292f"; radius: 4; border.color: "#424e56"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 12
                    Label { text: "PLAYLISTS"; color: "#9ef7ad"; font.bold: true; font.letterSpacing: 2 }
                    ListView {
                        Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 4
                        model: controller.playlists
                        delegate: ItemDelegate {
                            required property var modelData
                            width: ListView.view.width
                            text: modelData.name
                            highlighted: modelData.id === controller.selectedPlaylist
                            onClicked: { window.selectedTrack = -1; controller.selectPlaylist(modelData.id) }
                        }
                        ScrollBar.vertical: ScrollBar {}
                    }
                    TextField { id: playlistName; placeholderText: "New playlist name"; Layout.fillWidth: true; onAccepted: createPlaylistButton.clicked() }
                    Button { id: createPlaylistButton; text: "Create playlist"; Layout.fillWidth: true; onClicked: { controller.createPlaylist(playlistName.text); playlistName.clear() } }
                }
            }
            ColumnLayout {
                Layout.fillWidth: true; Layout.fillHeight: true
                RowLayout {
                    Label { text: "MUSIC LIBRARY"; color: "#9ef7ad"; font.bold: true; font.letterSpacing: 2 }
                    TextField { Layout.fillWidth: true; placeholderText: "Search title, artist, album"; onTextChanged: controller.search(text) }
                    CheckBox { text: "Favourites"; onToggled: controller.filterFavourites(checked) }
                }
                Rectangle {
                    Layout.fillWidth: true; Layout.fillHeight: true; color: "#171e22"; border.color: "#424e56"; radius: 4
                    ListView {
                        id: tracksView
                        anchors.fill: parent; anchors.margins: 4; clip: true
                        model: controller.tracks
                        delegate: Rectangle {
                            required property var modelData
                            required property int index
                            width: tracksView.width; height: 64
                            color: window.selectedTrack === modelData.id ? "#334c40" : (index % 2 ? "#1e282d" : "#172025")
                            RowLayout {
                                anchors.fill: parent; anchors.margins: 8
                                Button { text: modelData.favourite ? "\u2605" : "\u2606"; Layout.preferredWidth: 40; Accessible.name: "Toggle favourite"; onClicked: controller.toggleFavourite(modelData.id) }
                                ColumnLayout {
                                    Layout.fillWidth: true; spacing: 2
                                    Label { text: modelData.title; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
                                    Label { text: (modelData.artist || "Unknown artist") + "  /  " + (modelData.album || "Unknown album"); color: "#9eafb8"; font.pixelSize: 12; Layout.fillWidth: true; elide: Text.ElideRight }
                                }
                                Label { text: clock(modelData.duration * 1000); color: "#a9bdb0" }
                                Button { text: "Play"; onClicked: controller.playTrack(modelData.id) }
                            }
                            TapHandler {
                                acceptedButtons: Qt.LeftButton
                                onTapped: window.selectedTrack = modelData.id
                                onDoubleTapped: controller.playTrack(modelData.id)
                            }
                        }
                        ScrollBar.vertical: ScrollBar {}
                        Label { anchors.centerIn: parent; visible: tracksView.count === 0; text: "No tracks here yet.\nImport a folder or adjust your search and favourites filter."; color: "#a1b3bd"; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; width: parent.width - 32 }
                    }
                }
                RowLayout {
                    Layout.fillWidth: true
                    ComboBox { id: targetPlaylist; Layout.fillWidth: true; model: controller.playlists; textRole: "name"; valueRole: "id"; Accessible.name: "Destination playlist" }
                    Button { text: "Add selected"; enabled: window.selectedTrack > 0; onClicked: controller.addToPlaylist(window.selectedTrack, targetPlaylist.currentValue) }
                    Button { text: "Remove"; enabled: window.selectedTrack > 0 && controller.selectedPlaylist > 0; onClicked: controller.removeFromPlaylist(window.selectedTrack) }
                    Button { text: "Up"; enabled: window.selectedTrack > 0 && controller.selectedPlaylist > 0; Accessible.name: "Move selected track up"; onClicked: controller.moveTrack(window.selectedTrack, -1) }
                    Button { text: "Down"; enabled: window.selectedTrack > 0 && controller.selectedPlaylist > 0; Accessible.name: "Move selected track down"; onClicked: controller.moveTrack(window.selectedTrack, 1) }
                }
            }
        }
        ProgressBar { Layout.fillWidth: true; visible: controller.busy; value: controller.importProgress; indeterminate: controller.busy && controller.importProgress === 0 }
        RowLayout {
            Label { text: controller.status; color: "#bad0c2"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
            Button { text: "Details"; onClicked: detailsDialog.open() }
        }
        Label { text: "OFFLINE LOCAL PLAYER / MP3 / WAV / FLAC / OGG / M4A / Playback depends on Qt Multimedia codecs"; color: "#80949f"; font.pixelSize: 11; Layout.fillWidth: true; wrapMode: Text.WordWrap }
    }
}
