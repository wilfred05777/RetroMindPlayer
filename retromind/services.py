"""GUI-independent library importing and metadata extraction."""
import logging
import os
from pathlib import Path
import mutagen

EXTENSIONS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a'}
log = logging.getLogger(__name__)


def canonical_path(path):
    return os.path.normcase(str(Path(path).resolve(strict=True)))


def read_metadata(path):
    canonical = canonical_path(path)
    audio = mutagen.File(canonical, easy=True)
    if audio is None:
        raise ValueError('Unrecognized or invalid audio file')
    tags = audio.tags or {}
    def tag(key, fallback=''):
        value = tags.get(key)
        if not value:
            value = tags.get({'title': 'TIT2', 'artist': 'TPE1', 'album': 'TALB'}[key])
            if value is not None and hasattr(value, 'text'):
                value = value.text
        return str(value[0]) if value else fallback
    return dict(path=canonical, title=tag('title', Path(path).stem),
                artist=tag('artist'), album=tag('album'),
                duration=float(getattr(audio.info, 'length', 0) or 0))


class ImportService:
    def __init__(self, repository, metadata_reader=read_metadata):
        self.repository = repository
        self.metadata_reader = metadata_reader

    def scan(self, folder, progress=lambda done, total, message: None, cancelled=lambda: False):
        root = Path(folder)
        if not root.is_dir():
            raise ValueError('The selected music folder is unavailable.')
        paths, errors = [], []
        def walk_error(error):
            errors.append(str(error))
            log.warning('Folder scan: %s', error)
        for directory, _, names in os.walk(root, onerror=walk_error):
            if cancelled():
                break
            for name in names:
                if Path(name).suffix.lower() in EXTENSIONS:
                    paths.append(Path(directory) / name)
            progress(0, 0, f'Discovering music: {len(paths)} files found')
        added = duplicates = 0
        for index, path in enumerate(paths):
            if cancelled():
                break
            try:
                metadata = self.metadata_reader(path)
                metadata['path'] = canonical_path(path)
                if self.repository.add_track(metadata):
                    added += 1
                else:
                    duplicates += 1
            except Exception as error:
                message = f'{path.name}: {error}'
                errors.append(message)
                log.warning('Import skipped %s', path, exc_info=True)
            progress(index + 1, len(paths), path.name)
        return dict(added=added, duplicates=duplicates, errors=errors, cancelled=cancelled())
