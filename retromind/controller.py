import logging
from pathlib import Path
from PySide6.QtCore import QObject, Property, Signal, Slot, QThread, QUrl
from PySide6.QtMultimedia import QMediaPlayer
from .services import ImportService
from .playback import Playback

log = logging.getLogger(__name__)


class ImportWorker(QThread):
    progress = Signal(int, int, str)
    result = Signal(object)

    def __init__(self, repository, folder, parent=None):
        super().__init__(parent)
        self.repository, self.folder = repository, folder

    def run(self):
        try:
            result = ImportService(self.repository).scan(self.folder, self.progress.emit, self.isInterruptionRequested)
            self.result.emit(result)
        except Exception as error:
            log.exception('Import failed')
            self.result.emit(dict(added=0, duplicates=0, errors=[str(error)], cancelled=False))


class Controller(QObject):
    changed = Signal()
    playbackChanged = Signal()
    statusChanged = Signal()

    def __init__(self, repository):
        super().__init__()
        self.repo = repository
        self._query, self._favourites = '', False
        self._playlist = int(repository.setting('playlist', '0'))
        if self._playlist not in [p['id'] for p in repository.playlists()]:
            self._playlist = 0
        self._tracks, self._playlists, self._queue = [], [], []
        self._current, self._status, self._details = None, 'Ready. Import a music folder to begin.', ''
        self._busy, self._progress, self.worker = False, 0, None
        self._recorded = False
        self.playback = Playback(self)
        player = self.playback.player
        self.playback.audio.setVolume(float(repository.setting('volume', '0.7')))
        player.positionChanged.connect(self.playbackChanged)
        player.durationChanged.connect(self.playbackChanged)
        player.playbackStateChanged.connect(self.on_state)
        player.mediaStatusChanged.connect(self.on_media_status)
        player.errorOccurred.connect(self.on_error)
        self.refresh()

    def refresh(self):
        self._tracks = self.repo.tracks(self._query, self._favourites, self._playlist)
        self._playlists = [dict(id=0, name='All music')] + self.repo.playlists()
        self.changed.emit()

    tracks = Property('QVariantList', lambda self: self._tracks, notify=changed)
    playlists = Property('QVariantList', lambda self: self._playlists, notify=changed)
    selectedPlaylist = Property(int, lambda self: self._playlist, notify=changed)
    currentTitle = Property(str, lambda self: self._current['title'] if self._current else 'RETROMIND PLAYER', notify=playbackChanged)
    currentArtist = Property(str, lambda self: (self._current['artist'] or 'Unknown artist') if self._current else 'Your music. Your frequency.', notify=playbackChanged)
    position = Property(float, lambda self: self.playback.player.position(), notify=playbackChanged)
    duration = Property(float, lambda self: self.playback.player.duration(), notify=playbackChanged)
    playing = Property(bool, lambda self: self.playback.player.playbackState() == QMediaPlayer.PlayingState, notify=playbackChanged)
    volume = Property(float, lambda self: self.playback.audio.volume(), notify=playbackChanged)
    status = Property(str, lambda self: self._status, notify=statusChanged)
    errorDetails = Property(str, lambda self: self._details, notify=statusChanged)
    busy = Property(bool, lambda self: self._busy, notify=statusChanged)
    importProgress = Property(float, lambda self: self._progress, notify=statusChanged)

    def message(self, text):
        self._status = text
        self.statusChanged.emit()

    @Slot(str)
    def search(self, query):
        self._query = query
        self.refresh()

    @Slot(bool)
    def filterFavourites(self, enabled):
        self._favourites = enabled
        self.refresh()

    @Slot(int)
    def selectPlaylist(self, playlist_id):
        self._playlist = playlist_id
        self.repo.save_setting('playlist', playlist_id)
        self.refresh()

    @Slot(int)
    def toggleFavourite(self, track_id):
        self.repo.favourite(track_id)
        self.refresh()

    @Slot(str)
    def createPlaylist(self, name):
        try:
            self.selectPlaylist(self.repo.create_playlist(name))
        except ValueError as error:
            self.message(str(error))

    @Slot(int, int)
    def addToPlaylist(self, track_id, playlist_id):
        if playlist_id:
            self.repo.add_to_playlist(playlist_id, track_id)
            self.refresh()
            self.message('Track added to playlist.')
        else:
            self.message('Create or choose a named playlist first.')

    @Slot(int)
    def removeFromPlaylist(self, track_id):
        if self._playlist:
            self.repo.remove_from_playlist(self._playlist, track_id)
            self.refresh()

    @Slot(int, int)
    def moveTrack(self, track_id, direction):
        if self._playlist:
            self.repo.move_in_playlist(self._playlist, track_id, direction)
            self.refresh()

    @Slot(str)
    def importFolder(self, url):
        if self._busy:
            return
        self._busy, self._progress, self._details = True, 0, ''
        self.worker = ImportWorker(self.repo, QUrl(url).toLocalFile(), self)
        self.worker.progress.connect(self.on_progress)
        self.worker.result.connect(self.on_import_result)
        self.worker.finished.connect(self.on_worker_finished)
        self.message('Discovering music files...')
        self.worker.start()

    @Slot()
    def cancelImport(self):
        if self.worker:
            self.worker.requestInterruption()

    @Slot(int, int, str)
    def on_progress(self, done, total, name):
        self._progress = done / total if total else 0
        self.message(f'Importing {done}/{total}: {name}' if total else name)

    @Slot(object)
    def on_import_result(self, result):
        self._details = '\n'.join(result['errors'])
        self.message(f"{'Cancelled' if result['cancelled'] else 'Import complete'}: {result['added']} added, {result['duplicates']} duplicates, {len(result['errors'])} errors. See Details for errors.")
        self.refresh()

    @Slot()
    def on_worker_finished(self):
        self._busy = False
        self.worker.deleteLater()
        self.worker = None
        self.statusChanged.emit()

    @Slot(int)
    def playTrack(self, track_id):
        self._queue = [t['id'] for t in self._tracks]
        self.load_track(track_id)

    def load_track(self, track_id):
        track = self.repo.track(track_id)
        if not track or not Path(track['path']).is_file():
            self.playback.player.stop()
            self.message('This music file is missing. Restore it to its original folder or import its new location.')
            return
        self._current, self._recorded = track, False
        self.playback.load(track['path'])
        self.playbackChanged.emit()

    @Slot()
    def togglePlay(self):
        player = self.playback.player
        if self.playing:
            player.pause()
        elif self._current:
            if Path(self._current['path']).is_file():
                player.play()
            else:
                self.message('This music file is missing.')
        elif self._tracks:
            self.playTrack(self._tracks[0]['id'])
        else:
            self.message('No tracks available. Import a folder or clear your filters.')

    @Slot()
    def stop(self):
        self.playback.player.stop()

    @Slot(int)
    def step(self, direction):
        if not self._queue:
            self._queue = [t['id'] for t in self._tracks]
        if not self._queue:
            return
        current_id = self._current['id'] if self._current else None
        index = self._queue.index(current_id) if current_id in self._queue else (-1 if direction > 0 else len(self._queue))
        target = index + direction
        if 0 <= target < len(self._queue):
            self.load_track(self._queue[target])

    @Slot(float)
    def seek(self, position):
        if self.playback.player.isSeekable():
            self.playback.player.setPosition(int(position))

    @Slot(float)
    def setVolume(self, value):
        self.playback.audio.setVolume(max(0, min(1, value)))
        self.repo.save_setting('volume', self.playback.audio.volume())
        self.playbackChanged.emit()

    def on_state(self, state):
        if state == QMediaPlayer.PlayingState and self._current:
            if not self._recorded:
                self.repo.record_play(self._current['id'])
                self._recorded = True
            self.message('Playing: ' + self._current['title'])
        self.playbackChanged.emit()

    def on_media_status(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.step(1)

    def on_error(self, error, message):
        log.error('Playback: %s', message)
        self.message('Cannot play this file: ' + message + ' Playback support depends on the codecs bundled with Qt Multimedia.')

    @Slot()
    def shutdown(self):
        if self.worker:
            self.worker.requestInterruption()
            self.worker.wait()
        self.playback.player.stop()
