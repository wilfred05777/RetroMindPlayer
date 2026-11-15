"""Presentation controller: commands/properties, lifecycle and application coordination."""
import logging
from pathlib import Path
from PySide6.QtCore import QObject, Property, Signal, Slot, QThread, QUrl, QTimer, QStandardPaths
from PySide6.QtMultimedia import QMediaPlayer, QMediaFormat, QVideoFrame
from .services import ImportService
from .playback import Playback
from .queue_service import PlayQueue
from .artwork import ArtworkManager

log = logging.getLogger(__name__)


class ImportWorker(QThread):
    progress = Signal(int, int, str)
    result = Signal(object)

    def __init__(self, repository, sources, folder=False, parent=None, discover=False, report=None):
        super().__init__(parent)
        self.repository, self.sources, self.folder = repository, sources, folder
        self.discover, self.report = discover, report

    def run(self):
        try:
            service = ImportService(self.repository)
            if self.discover:
                result = service.discover(self.sources, self.progress.emit, self.isInterruptionRequested)
            elif self.folder:
                result = service.scan(self.sources, self.progress.emit, self.isInterruptionRequested)
            else:
                result = service.import_paths(self.sources, self.progress.emit, self.isInterruptionRequested, discovery=self.report)
            self.result.emit(result)
        except Exception as error:
            log.exception('Import failed')
            self.result.emit(dict(kind='discovery' if self.discover else 'import', added=0, duplicates=0, discovered=0, skipped=0, failed=1, entries=[], paths=[], errors=[str(error)], cancelled=False))


class Controller(QObject):
    changed = Signal()
    playbackChanged = Signal()
    statusChanged = Signal()
    layoutChanged = Signal()
    artworkReady = Signal(int, str)
    clearVideo = Signal()
    queueChanged = Signal()
    previewChanged = Signal()
    # Future assistant tools should call application services; no assistant UI or model dependency.

    def __init__(self, repository):
        super().__init__()
        self.repo = repository
        self._closing = False
        self._preview_report = {}
        self._query, self._favourites = '', False
        self._playlist = self._int_setting('playlist', 0)
        if self._playlist not in [p['id'] for p in repository.playlists()]:
            self._playlist = 0
        self._view = 'playlist' if self._playlist else repository.setting('view', 'home')
        self._filter, self._sort = 'all', 'title'
        self._tracks, self._playlists, self._queue_snapshot = [], [], []
        self._current, self._status, self._details = None, 'Your local music and videos, together.', ''
        self._busy, self._progress, self.worker = False, 0, None
        self._recorded, self._resume_position = False, 0
        self._video_frame_seen = False
        self._failed = set()
        self._automatic_transition = False
        self.queue = PlayQueue(repository.setting('shuffle', '0') == '1', repository.setting('repeat', 'off'))
        self._right = repository.setting('right_panel', '1') == '1'
        self._sidebar = repository.setting('sidebar', '1') == '1'
        self._grid = repository.setting('grid', '0') == '1'
        self._video_visible, self._fullscreen = True, False
        self.playback = Playback(self)
        player = self.playback.player
        self.playback.audio.setVolume(max(0, min(1, self._float_setting('volume', .7))))
        self.playback.audio.setMuted(repository.setting('muted', '0') == '1')
        player.positionChanged.connect(self.on_position)
        player.durationChanged.connect(self.playbackChanged)
        player.playbackStateChanged.connect(self.on_state)
        player.mediaStatusChanged.connect(self.on_media_status)
        player.errorOccurred.connect(self.on_error)
        player.hasVideoChanged.connect(self.on_streams)
        player.metaDataChanged.connect(self.playbackChanged)
        self.artwork = ArtworkManager(Path(repository.path).parent / 'thumbnails', self)
        self.artwork.ready.connect(self.artworkReady)
        self._pending_video_frame = QVideoFrame()
        self._pending_video_id = None
        self._repaint_timer = QTimer(self)
        self._repaint_timer.setSingleShot(True)
        self._repaint_timer.timeout.connect(self.resubmit_paused_frame)
        self._bookmark_timer = QTimer(self)
        self._bookmark_timer.setInterval(5000)
        self._bookmark_timer.timeout.connect(self.save_bookmark)
        self._bookmark_timer.start()
        self.refresh()

    def _int_setting(self, key, default):
        try:
            return int(self.repo.setting(key, str(default)))
        except ValueError:
            return default

    def _float_setting(self, key, default):
        try:
            return float(self.repo.setting(key, str(default)))
        except ValueError:
            return default

    def refresh(self):
        view = self._view if self._view in ('favourites', 'recently_added', 'recently_played') else 'all'
        self._tracks = self.repo.tracks(self._query, self._favourites, self._playlist, self._filter, self._sort, view)
        self._playlists = [dict(id=0, name='Choose playlist')] + self.repo.playlists()
        self.changed.emit()
        self.playbackChanged.emit()

    importPreview = Property('QVariantList', lambda self: self._preview_report.get('entries', []), notify=previewChanged)
    importPreviewSummary = Property(str, lambda self: f"Discovered: {self._preview_report.get('discovered', 0)} supported files; skipped: {self._preview_report.get('skipped', 0)}; failed folders: {len(self._preview_report.get('errors', []))}", notify=previewChanged)
    canImportPreview = Property(bool, lambda self: bool(self._preview_report.get('paths')) and not self._preview_report.get('cancelled', False), notify=previewChanged)

    downloadsFolder = Property(str, lambda self: QUrl.fromLocalFile(QStandardPaths.writableLocation(QStandardPaths.DownloadLocation)).toString(), constant=True)

    tracks = Property('QVariantList', lambda self: self._tracks, notify=changed)
    playlists = Property('QVariantList', lambda self: self._playlists, notify=changed)
    selectedPlaylist = Property(int, lambda self: self._playlist, notify=changed)
    mediaFilter = Property(str, lambda self: self._filter, notify=changed)
    sortOrder = Property(str, lambda self: self._sort, notify=changed)
    view = Property(str, lambda self: self._view, notify=changed)
    viewTitle = Property(str, lambda self: next((p['name'] for p in self._playlists if p['id'] == self._playlist), 'Playlist') if self._playlist else {'home': 'Made for your moments', 'all': 'All media', 'favourites': 'Favourites', 'recently_added': 'Recently added', 'recently_played': 'Recently played'}.get(self._view, 'Your library'), notify=changed)
    totalDuration = Property(float, lambda self: sum(t['duration'] or 0 for t in self._tracks), notify=changed)
    recentAdded = Property('QVariantList', lambda self: self.repo.tracks(view='recently_added', limit=8), notify=changed)
    recentPlayed = Property('QVariantList', lambda self: self.repo.tracks(view='recently_played', limit=8), notify=changed)
    continueTrack = Property('QVariantMap', lambda self: self.repo.track(self._int_setting('last_track', 0)) or {}, notify=changed)
    currentTrack = Property('QVariantMap', lambda self: self._current or {}, notify=playbackChanged)
    currentTitle = Property(str, lambda self: self._current['title'] if self._current else 'Nothing playing yet', notify=playbackChanged)
    currentArtist = Property(str, lambda self: (self._current['artist'] or 'Unknown artist') if self._current else 'Pick something from your library', notify=playbackChanged)
    position = Property(float, lambda self: self.playback.player.position(), notify=playbackChanged)
    duration = Property(float, lambda self: self.playback.player.duration(), notify=playbackChanged)
    playing = Property(bool, lambda self: self.playback.player.playbackState() == QMediaPlayer.PlayingState, notify=playbackChanged)
    volume = Property(float, lambda self: self.playback.audio.volume(), notify=playbackChanged)
    muted = Property(bool, lambda self: self.playback.audio.isMuted(), notify=playbackChanged)
    hasVideo = Property(bool, lambda self: self.playback.player.hasVideo(), notify=playbackChanged)
    videoVisible = Property(bool, lambda self: self._video_visible, notify=layoutChanged)
    fullscreen = Property(bool, lambda self: self._fullscreen, notify=layoutChanged)
    rightPanel = Property(bool, lambda self: self._right, notify=layoutChanged)
    sidebar = Property(bool, lambda self: self._sidebar, notify=layoutChanged)
    grid = Property(bool, lambda self: self._grid, notify=layoutChanged)
    shuffle = Property(bool, lambda self: self.queue.shuffle, notify=playbackChanged)
    repeat = Property(str, lambda self: self.queue.repeat, notify=playbackChanged)
    queueTracks = Property('QVariantList', lambda self: self._queue_snapshot, notify=queueChanged)
    status = Property(str, lambda self: self._status, notify=statusChanged)
    errorDetails = Property(str, lambda self: self._details, notify=statusChanged)
    busy = Property(bool, lambda self: self._busy, notify=statusChanged)
    importProgress = Property(float, lambda self: self._progress, notify=statusChanged)
    sidebarWidth = Property(int, lambda self: max(190, min(340, self._int_setting('sidebar_width', 248))), constant=True)
    rightWidth = Property(int, lambda self: max(250, min(390, self._int_setting('right_width', 292))), constant=True)
    windowWidth = Property(int, lambda self: max(800, self._int_setting('window_width', 1440)), constant=True)
    windowHeight = Property(int, lambda self: max(600, self._int_setting('window_height', 900)), constant=True)
    capabilities = Property(str, lambda self: 'Qt reports video decoders: ' + ', '.join(QMediaFormat.videoCodecDescription(c) for c in QMediaFormat().supportedVideoCodecs(QMediaFormat.Decode)) + '. These are capability hints; actual files may still fail. Containers are not codecs.', constant=True)

    def message(self, text):
        self._status = text
        self.statusChanged.emit()

    @Slot(str)
    def search(self, query):
        self._query = query
        if query and self._view == 'home':
            self._view, self._playlist = 'all', 0
        self.refresh()

    @Slot(str)
    def navigate(self, view):
        self._playlist, self._view = 0, view
        self._favourites = False
        self.repo.save_setting('playlist', 0)
        self.repo.save_setting('view', view)
        self.refresh()

    @Slot(str)
    def setMediaFilter(self, value):
        self._filter = value if value in ('all', 'audio', 'video') else 'all'
        self.refresh()

    @Slot(str)
    def setSort(self, value):
        self._sort = value
        self.refresh()

    @Slot(bool)
    def filterFavourites(self, enabled):
        self._favourites = enabled
        self.refresh()

    @Slot(int)
    def selectPlaylist(self, playlist_id):
        self._playlist, self._view = playlist_id, 'playlist' if playlist_id else 'all'
        self._favourites = False
        self.repo.save_setting('playlist', playlist_id)
        self.refresh()

    @Slot(int)
    def toggleFavourite(self, track_id):
        self.repo.favourite(track_id)
        if self._current and track_id == self._current['id']:
            self._current = self.repo.track(track_id)
        self.refresh()

    @Slot(str)
    def createPlaylist(self, name):
        try:
            self.selectPlaylist(self.repo.create_playlist(name))
        except ValueError as error:
            self.message(str(error))

    @Slot(str)
    def renamePlaylist(self, name):
        if self._playlist:
            try:
                self.repo.rename_playlist(self._playlist, name)
                self.refresh()
            except ValueError as error:
                self.message(str(error))

    @Slot(int, int)
    def addToPlaylist(self, track_id, playlist_id):
        if playlist_id and track_id > 0:
            self.repo.add_to_playlist(playlist_id, track_id)
            self.refresh()
            self.message('Added to playlist.')
        else:
            self.message('Select a media item and a named playlist first.')

    @Slot(int)
    def removeFromPlaylist(self, track_id):
        if self._playlist:
            self.repo.remove_from_playlist(self._playlist, track_id)
            self.refresh()

    @Slot(int, int)
    def moveTrack(self, track_id, direction):
        if self._playlist:
            self.repo.move_in_playlist(self._playlist, track_id, direction)
            self._sort = 'title'  # Manual playlist order.
            self.refresh()

    def start_import(self, sources, folder=False, discover=False, report=None):
        if self._busy:
            self.message('An import is already running. Wait or cancel it first.')
            return
        self._busy, self._progress, self._details = True, 0, ''
        self.worker = ImportWorker(self.repo, sources, folder, self, discover, report)
        self.worker.progress.connect(self.on_progress)
        self.worker.result.connect(self.on_import_result)
        self.worker.finished.connect(self.on_worker_finished)
        self.message('Discovering local media...')
        self.worker.start()

    @Slot(str)
    def previewFolder(self, url):
        if self._busy:
            return
        if not url or (not QUrl(url).isLocalFile() and not Path(url).is_absolute()):
            self.message('Choose a local folder before scanning.')
            return
        self._preview_report = {}
        self.previewChanged.emit()
        local = QUrl(url).toLocalFile() if QUrl(url).isLocalFile() else url
        self.start_import(local, discover=True)

    @Slot()
    def importDiscovered(self):
        if self.canImportPreview and not self._busy:
            self.start_import(self._preview_report['paths'], report=self._preview_report)

    @Slot(str)
    def importFolder(self, url):
        local = QUrl(url).toLocalFile()
        if local:
            self.start_import(local, True)
        else:
            self.message('Choose a local folder before importing.')

    @Slot('QVariantList')
    def importFiles(self, urls):
        paths = []
        for item in urls:
            url = QUrl(item)
            if url.isLocalFile():
                paths.append(url.toLocalFile())
        if paths:
            self.start_import(paths)
        else:
            self.message('Drop or choose local media files. Remote URLs are not imported.')

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
        self._details = '\n'.join(result.get('errors', []) + result.get('warnings', []) + result.get('reasons', []))
        if result.get('kind') == 'discovery':
            self._preview_report = result
            self.previewChanged.emit()
            self.message(('Scan cancelled. ' if result['cancelled'] else 'Scan complete. ') + self.importPreviewSummary + '. Review the preview before importing.')
            return
        self.message(f"{'Cancelled' if result['cancelled'] else 'Import complete'}: {result.get('discovered', 0)} discovered, {result['added']} imported, {result.get('skipped', result['duplicates'])} skipped, {result.get('failed', len(result['errors']))} failed; {len(result.get('warnings', []))} warnings, {result.get('pending', 0)} pending. See Details for reasons.")
        self.refresh()

    @Slot()
    def on_worker_finished(self):
        self._busy = False
        if self.worker:
            self.worker.deleteLater()
            self.worker = None
        self.statusChanged.emit()

    @Slot(int)
    def requestArtwork(self, track_id):
        track = self.repo.track(track_id)
        if track:
            self.artwork.request(track)

    @Slot(QObject)
    def attachVideo(self, sink):
        self.playback.player.setVideoSink(sink)
        sink.videoFrameChanged.connect(self.on_video_frame)

    @Slot(int)
    def playTrack(self, track_id):
        self._automatic_transition = False
        self._failed.clear()
        self.queue.start([t['id'] for t in self._tracks], track_id)
        self.load_track(track_id)

    @Slot()
    def playView(self):
        if self._tracks:
            self.playTrack(self._tracks[0]['id'])

    @Slot()
    def resumeLast(self):
        track_id = self._int_setting('last_track', 0)
        position = self._int_setting('last_position', 0)
        if self.repo.track(track_id):
            self.playTrack(track_id)
            self._resume_position = position

    def refresh_queue(self):
        self._queue_snapshot = self.repo.tracks_by_ids(self.queue.upcoming)
        self.queueChanged.emit()

    def load_track(self, track_id):
        self.refresh_queue()
        self.save_bookmark()
        track = self.repo.track(track_id)
        self._resume_position = 0
        self._video_frame_seen = False
        self.clearVideo.emit()
        self._recorded = False
        if not track or not Path(track['path']).is_file():
            self.playback.player.stop()
            self.playback.player.setSource(QUrl())
            self._current = track
            self._failed.add(track_id)
            self.message('This media file is missing. Restore it or import its new location. Use Next to continue.')
            self.playbackChanged.emit()
            return False
        self._current, self._recorded = track, False
        self.playback.load(track['path'])
        self.requestArtwork(track_id)
        self.playbackChanged.emit()
        return True

    @Slot()
    def togglePlay(self):
        player = self.playback.player
        if self.playing:
            player.pause()
        elif self._current:
            if not Path(self._current['path']).is_file():
                self.message('This media file is missing.')
            elif player.source().isEmpty():
                self.load_track(self._current['id'])
            else:
                player.play()
        else:
            self.playView()

    @Slot()
    def stop(self):
        self.playback.player.stop()

    @Slot(int)
    def step(self, direction):
        self.advance(direction, False)

    def advance(self, direction=1, automatic=False):
        if self._closing:
            return
        self._automatic_transition = automatic
        if not self.queue.items and self._tracks:
            self.queue.start([t['id'] for t in self._tracks], self._tracks[0]['id'])
            self.load_track(self.queue.current)
            return
        for _ in range(len(self.queue.items)):
            track_id = self.queue.advance(direction, automatic)
            if track_id is None:
                return
            if track_id in self._failed:
                automatic = False  # Do not repeat a failed item forever.
                continue
            if self.load_track(track_id):
                return
            automatic = False
        self.message('No available items remain in this queue. See Details or the log for playback errors.')

    @Slot(int)
    def playQueued(self, track_id):
        self._failed.discard(track_id)
        if self.queue.select(track_id):
            self.load_track(track_id)

    @Slot(int)
    def removeQueued(self, track_id):
        self.queue.remove(track_id)
        self.refresh_queue()
        self.playbackChanged.emit()

    @Slot()
    def toggleShuffle(self):
        self.queue.set_shuffle(not self.queue.shuffle)
        self.refresh_queue()
        self.repo.save_setting('shuffle', int(self.queue.shuffle))
        self.playbackChanged.emit()

    @Slot()
    def cycleRepeat(self):
        modes = ['off', 'all', 'one']
        self.queue.repeat = modes[(modes.index(self.queue.repeat) + 1) % 3]
        self.repo.save_setting('repeat', self.queue.repeat)
        self.playbackChanged.emit()

    @Slot(float)
    def seek(self, position):
        if self.playback.player.isSeekable():
            self.playback.player.setPosition(int(position))

    @Slot(float)
    def setVolume(self, value):
        self.playback.audio.setVolume(max(0, min(1, value)))
        self.repo.save_setting('volume', self.playback.audio.volume())
        self.playbackChanged.emit()

    @Slot()
    def toggleMute(self):
        muted = not self.playback.audio.isMuted()
        self.playback.audio.setMuted(muted)
        self.repo.save_setting('muted', int(muted))
        self.playbackChanged.emit()

    @Slot(str)
    def togglePanel(self, panel):
        if panel == 'right':
            self._right = not self._right
            self.repo.save_setting('right_panel', int(self._right))
        elif panel == 'sidebar':
            self._sidebar = not self._sidebar
            self.repo.save_setting('sidebar', int(self._sidebar))
        elif panel == 'grid':
            self._grid = not self._grid
            self.repo.save_setting('grid', int(self._grid))
        elif panel == 'video':
            self._video_visible = not self._video_visible
        self.layoutChanged.emit()
        if panel == 'video' and self._video_visible:
            self.repaint_paused_video()

    @Slot()
    def toggleFullscreen(self):
        if self.hasVideo:
            self._fullscreen = not self._fullscreen
            self._video_visible = True
            self.layoutChanged.emit()
            self.repaint_paused_video()

    @Slot()
    def exitFullscreen(self):
        if self._fullscreen:
            self._fullscreen = False
            self.layoutChanged.emit()
            self.repaint_paused_video()

    def repaint_paused_video(self):
        # Own the timer and frame so shutdown can release them before Qt surfaces.
        sink = self.playback.player.videoSink()
        self._pending_video_frame = QVideoFrame(sink.videoFrame()) if sink else QVideoFrame()
        self._pending_video_id = self._current['id'] if self._current else None
        self._repaint_timer.start(120)

    def resubmit_paused_frame(self):
        frame = self._pending_video_frame
        self._pending_video_frame = QVideoFrame()
        if self._closing or self.playing or not self._current or self._current['id'] != self._pending_video_id:
            return
        sink = self.playback.player.videoSink()
        if sink and frame.isValid():
            sink.setVideoFrame(QVideoFrame())
            sink.setVideoFrame(frame)

    @Slot(int, int)
    def savePanelWidths(self, sidebar, right):
        self.repo.save_setting('sidebar_width', sidebar)
        self.repo.save_setting('right_width', right)

    @Slot(int, int)
    def saveWindow(self, width, height):
        if not self._fullscreen:
            self.repo.save_setting('window_width', width)
            self.repo.save_setting('window_height', height)

    def on_position(self, position):
        self.playbackChanged.emit()

    def on_video_frame(self, frame):
        if frame.isValid():
            self._video_frame_seen = True

    def on_streams(self, *args):
        if not self.playback.player.hasVideo():
            self.clearVideo.emit()
            self.exitFullscreen()
        self.playbackChanged.emit()

    def on_state(self, state):
        if state == QMediaPlayer.PlayingState and self._current:
            if not self._recorded:
                self.repo.record_play(self._current['id'])
                self._recorded = True
                self.changed.emit()
            self.message('Playing: ' + self._current['title'])
        self.playbackChanged.emit()

    def on_media_status(self, status):
        if self._closing:
            return
        if status in (QMediaPlayer.LoadedMedia, QMediaPlayer.BufferedMedia) and self._resume_position:
            self.playback.player.setPosition(self._resume_position)
            self._resume_position = 0
        if status == QMediaPlayer.EndOfMedia:
            if self._current and self._current.get('has_video') and not self._video_frame_seen:
                self.on_error(QMediaPlayer.FormatError, 'No video frames were decoded; this video codec may be unsupported by the installed Qt backend')
                return
            self.advance(1, True)

    def on_error(self, error, message):
        if self._closing:
            return
        path = self._current['path'] if self._current else '(unknown source)'
        log.error('Playback error %s: %s [%s]', error, message, path)
        self._details = f'{path}\n{error}: {message}\n' + self._details
        if self._current:
            self._failed.add(self._current['id'])
        self.message('Cannot play this file: ' + message + '. Playback depends on Qt codecs. Use Next to continue.')
        self.clearVideo.emit()
        self.exitFullscreen()
        if self._automatic_transition and self._current:
            failed_id = self._current['id']
            QTimer.singleShot(0, lambda: self.advance(1, True)
                              if self._current and self._current['id'] == failed_id else None)

    def save_bookmark(self):
        if self._current and self._recorded:
            self.repo.save_setting('last_track', self._current['id'])
            self.repo.save_setting('last_position', self.playback.player.position())

    @Slot()
    def shutdown(self):
        if self._closing:
            return
        self._closing = True
        self._bookmark_timer.stop()
        self._repaint_timer.stop()
        self._pending_video_frame = QVideoFrame()
        self.save_bookmark()
        if self.worker:
            self.worker.requestInterruption()
            self.worker.wait()
        self.artwork.shutdown()
        self.playback.player.blockSignals(True)
        self.playback.player.stop()
        self.playback.player.setSource(QUrl())
        self.playback.player.setVideoSink(None)
        self.playback.player.deleteLater()
        self.playback.audio.deleteLater()
