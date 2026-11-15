import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs

Dialog {
    id: dialog
    objectName: "folderImportDialog"
    title: "Preview folder import"
    modal: true
    anchors.centerIn: parent
    width: Math.min(parent.width - 40, 900)
    height: Math.min(parent.height - 40, 620)
    property string initialFolder: ""
    property url selectedFolder: initialFolder
    property var previewEntries: []
    property string previewSummary: "Choose a folder to discover supported media recursively."
    property bool scanning: false
    property bool readyToImport: false
    signal scanRequested(string folderUrl)
    signal importRequested()
    signal cancelRequested()
    function selectFolder() { nativePicker.open() }
    function previewFolderSelection(folderUrl: url): void {
        if (!folderUrl.toString()) return
        dialog.selectedFolder = folderUrl
        dialog.open()
        dialog.scanRequested(folderUrl.toString())
    }
    FolderDialog {
        id: nativePicker
        objectName: "nativeImportFolderPicker"
        title: "Select a folder; files will appear in the next preview."
        currentFolder: dialog.selectedFolder
        onAccepted: dialog.previewFolderSelection(selectedFolder)
    }
    contentItem: ColumnLayout {
        spacing: 12
        Label { text: "Select a folder; files will appear in the next preview."; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        RowLayout {
            Layout.fillWidth: true
            Label { text: dialog.selectedFolder.toString(); Layout.fillWidth: true; elide: Text.ElideMiddle; ToolTip.visible: folderHover.hovered; ToolTip.text: text; HoverHandler { id: folderHover } }
            Button { text: "Select folder..."; enabled: !dialog.scanning; onClicked: nativePicker.open() }
            Button { text: "Scan again"; enabled: !dialog.scanning && dialog.selectedFolder.toString() !== ""; onClicked: dialog.scanRequested(dialog.selectedFolder.toString()) }
        }
        Label { text: dialog.scanning ? "Working... " + dialog.previewSummary : dialog.previewSummary; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        Label { text: "Includes subfolders. Discovery does not validate codecs. Skipped files and their reasons are shown below."; color: "#B3B3B3"; wrapMode: Text.WordWrap; Layout.fillWidth: true }
        ListView {
            id: files
            objectName: "importPreviewList"
            Layout.fillWidth: true; Layout.fillHeight: true
            clip: true
            model: dialog.previewEntries
            ScrollBar.vertical: ScrollBar {}
            delegate: ItemDelegate {
                required property var modelData
                width: files.width
                text: modelData.state + "   " + modelData.name + (modelData.reason ? " — " + modelData.reason : "")
                Accessible.name: text
                ToolTip.visible: hovered
                ToolTip.text: modelData.path + (modelData.reason ? "\n" + modelData.reason : "")
            }
            Label { anchors.centerIn: parent; width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; visible: files.count === 0; text: dialog.scanning ? "Scanning folder..." : "No files discovered. Select a folder or review Details for scan errors."; color: "#B3B3B3" }
        }
        Label { text: "Videos still import when metadata is unavailable. Artwork is optional. See Details for warnings and failures."; wrapMode: Text.WordWrap; Layout.fillWidth: true; color: "#B3B3B3" }
        RowLayout {
            Layout.alignment: Qt.AlignRight
            Button { text: dialog.scanning ? "Cancel scan" : "Cancel"; onClicked: { if (dialog.scanning) dialog.cancelRequested(); dialog.reject() } }
            Button { text: "Import discovered files"; enabled: !dialog.scanning && dialog.readyToImport; onClicked: { dialog.importRequested(); dialog.accept() } }
        }
    }
}
