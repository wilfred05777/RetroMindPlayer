"""Qt Multimedia integration; all instances remain on the GUI thread."""
from PySide6.QtCore import QObject, QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer


class Playback(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.audio = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio)

    def load(self, path):
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()
