"""Lazy, bounded background artwork generation with source-versioned disk cache."""
import hashlib
import logging
from pathlib import Path
import av
import mutagen
from .services import filesystem_path
from PySide6.QtCore import QObject, Signal, Slot, QRunnable, QThreadPool, QUrl
from PySide6.QtGui import QImage

log = logging.getLogger(__name__)


def cache_key(path):
    path = Path(path)
    stat = path.stat()
    return hashlib.sha256(f'{path.resolve()}:{stat.st_size}:{stat.st_mtime_ns}'.encode()).hexdigest()


def image_for_media(path):
    # Embedded covers first, including MP3/FLAC/MP4/OGG. No GUI objects in worker.
    try:
        audio = mutagen.File(filesystem_path(path))
        if audio is not None:
            data = None
            if getattr(audio, 'pictures', None):
                data = audio.pictures[0].data
            elif audio.tags:
                if hasattr(audio.tags, 'getall') and audio.tags.getall('APIC'):
                    data = audio.tags.getall('APIC')[0].data
                elif audio.tags.get('covr'):
                    data = bytes(audio.tags['covr'][0])
                elif audio.tags.get('metadata_block_picture'):
                    import base64
                    from mutagen.flac import Picture
                    data = Picture(base64.b64decode(audio.tags['metadata_block_picture'][0])).data
            if data:
                image = QImage.fromData(data)
                if not image.isNull():
                    return image
    except Exception:
        log.debug('No embedded artwork: %s', path, exc_info=True)
    with av.open(filesystem_path(path), metadata_errors='replace', timeout=8) as container:
        streams = list(container.streams.video)
        if not streams:
            return QImage()
        # Decode only until the first picture, not the rest of the video.
        stream = streams[0]
        for frame in container.decode(stream):
            width = min(480, frame.width)
            height = max(1, round(frame.height * width / frame.width))
            rgb = frame.reformat(width=width, height=height, format='rgb24')
            return QImage(bytes(rgb.planes[0]), width, height, rgb.planes[0].line_size,
                          QImage.Format_RGB888).copy()
    return QImage()


class ArtworkSignals(QObject):
    ready = Signal(int, str, str)


class ArtworkTask(QRunnable):
    def __init__(self, track_id, path, cache, signals):
        super().__init__()
        self.track_id, self.path, self.cache, self.signals = track_id, path, cache, signals

    def run(self):
        key = ''
        url = ''
        try:
            key = cache_key(self.path)
            target = self.cache / (key + '.jpg')
            absent = self.cache / (key + '.empty')
            if not target.exists() and not absent.exists():
                image = image_for_media(self.path)
                if image.isNull():
                    absent.touch()
                else:
                    from PySide6.QtCore import Qt
                    image = image.scaled(480, 480, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    if not image.save(str(target), 'JPEG', 85):
                        raise OSError('Could not save cached artwork')
            if target.exists():
                url = QUrl.fromLocalFile(str(target)).toString()
        except Exception:
            log.debug('Artwork unavailable: %s', self.path, exc_info=True)
        self.signals.ready.emit(self.track_id, key, url)


class ArtworkManager(QObject):
    ready = Signal(int, str)

    def __init__(self, cache, parent=None):
        super().__init__(parent)
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(2)
        self.signals = ArtworkSignals(self)
        self.signals.ready.connect(self.on_ready)
        self.pending = set()
        self.results = {}

    def request(self, track):
        track_id = track['id']
        # Even cache hits/stat calls run in workers, including network paths.
        if track_id not in self.pending:
            self.pending.add(track_id)
            self.pool.start(ArtworkTask(track_id, track['path'], self.cache, self.signals))

    @Slot(int, str, str)
    def on_ready(self, track_id, key, url):
        self.pending.discard(track_id)
        self.results[track_id] = (key, url)
        self.ready.emit(track_id, url)

    def shutdown(self):
        self.pool.clear()
        self.pool.waitForDone()
