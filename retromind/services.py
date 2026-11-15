"""GUI-independent library importing and metadata extraction."""
import logging
import os
from pathlib import Path
import mutagen

AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.ogg', '.m4a'}
VIDEO_EXTENSIONS = {'.mp4', '.m4v', '.mkv', '.webm', '.mov', '.avi', '.wmv', '.mpg', '.mpeg', '.ts', '.m2ts'}
EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS
log = logging.getLogger(__name__)


def filesystem_path(path):
    """Use extended Windows paths for I/O, without changing stored library keys."""
    value = os.path.abspath(os.fspath(path))
    if os.name == 'nt' and not value.startswith('\\\\?\\') and len(value) >= 248:
        return '\\\\?\\UNC\\' + value[2:] if value.startswith('\\\\') else '\\\\?\\' + value
    return value


def canonical_path(path):
    value = str(Path(filesystem_path(path)).resolve(strict=True))
    if value.startswith('\\\\?\\UNC\\'):
        value = '\\\\' + value[8:]
    elif value.startswith('\\\\?\\'):
        value = value[4:]
    return os.path.normcase(value)


def read_audio_metadata(path):
    canonical = canonical_path(path)
    audio = mutagen.File(filesystem_path(canonical), easy=True)
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


def read_metadata(path):
    import av
    canonical = canonical_path(path)
    result = dict(path=canonical, title=Path(path).stem, artist='', album='', duration=0,
                  media_type='unknown', width=None, height=None, video_codec=None,
                  audio_codec=None, container=None, has_audio=None, has_video=None)
    # Probe stream headers, never decode a whole video for indexing.
    try:
        with av.open(filesystem_path(canonical), metadata_errors='replace', timeout=8) as container:
            video = [stream for stream in container.streams.video
                     if not (stream.disposition & av.stream.Disposition.attached_pic)]
            audio = list(container.streams.audio)
            result.update(media_type='video' if video else 'audio' if audio else 'unknown',
                          duration=float(container.duration / av.time_base) if container.duration else 0,
                          container=container.format.name, has_audio=bool(audio), has_video=bool(video))
            tags = {key.lower(): value for key, value in container.metadata.items()}
            result.update(title=tags.get('title') or Path(path).stem,
                          artist=tags.get('artist', ''), album=tags.get('album', ''))
            if video:
                context = video[0].codec_context
                result.update(width=context.width or None, height=context.height or None,
                              video_codec=context.name)
            if audio:
                result['audio_codec'] = audio[0].codec_context.name
            if not audio and not video:
                raise ValueError('No playable audio or video stream found')
    except Exception:
        if Path(path).suffix.lower() not in AUDIO_EXTENSIONS:
            raise
        # Mutagen can read some audio types without an installed decoder.
        result.update(read_audio_metadata(path), media_type='audio')
        return result
    if result['media_type'] == 'audio':
        try:
            result.update(read_audio_metadata(path))
        except Exception:
            pass  # Container metadata remains usable.
    return result


class ImportService:
    def __init__(self, repository, metadata_reader=read_metadata):
        self.repository = repository
        self.metadata_reader = metadata_reader

    def discover(self, folder, progress=lambda done, total, message: None, cancelled=lambda: False):
        root = Path(filesystem_path(folder))
        if not root.is_dir():
            raise ValueError('The selected media folder is unavailable.')
        paths, entries, errors = [], [], []
        skipped = 0
        def walk_error(error):
            errors.append(f'{error.filename}: {error.strerror}')
            entries.append(dict(path=str(error.filename), name=str(error.filename), state='Failed', reason=error.strerror or str(error)))
            log.warning('Folder scan: %s', error)
        for directory, dirs, names in os.walk(root, onerror=walk_error):
            if cancelled():
                break
            dirs.sort(key=str.casefold)
            for name in sorted(names, key=str.casefold):
                if cancelled():
                    break
                path = Path(directory) / name
                supported = path.suffix.lower() in EXTENSIONS
                if supported:
                    paths.append(str(path))
                else:
                    skipped += 1
                entries.append(dict(path=str(path), name=str(path.relative_to(root)),
                                    state='Discovered' if supported else 'Skipped',
                                    reason='' if supported else 'Unsupported extension'))
            progress(0, 0, f'Discovering media: {len(paths)} supported, {skipped} skipped')
        return dict(kind='discovery', paths=paths, entries=entries, discovered=len(paths),
                    skipped=skipped, errors=errors, cancelled=cancelled())

    def scan(self, folder, progress=lambda done, total, message: None, cancelled=lambda: False):
        report = self.discover(folder, progress, cancelled)
        return self.import_paths(report['paths'], progress, cancelled, discovery=report)

    def import_paths(self, paths, progress=lambda done, total, message: None,
                     cancelled=lambda: False, errors=None, discovery=None):
        paths = list(paths)
        errors = list(errors or []) + list((discovery or {}).get('errors', []))
        warnings, reasons = [], []
        if discovery:
            reasons.extend(f"{e['path']}: {e['reason']}" for e in discovery['entries'] if e['state'] == 'Skipped')
        added = duplicates = 0
        skipped = (discovery or {}).get('skipped', 0)
        discovered = (discovery or {}).get('discovered', sum(Path(p).suffix.lower() in EXTENSIONS for p in paths))
        processed = 0
        for index, path in enumerate(paths):
            if cancelled():
                break
            path = Path(path)
            processed += 1
            if path.suffix.lower() not in EXTENSIONS:
                skipped += 1
                reasons.append(f'{path}: Unsupported extension')
                continue
            try:
                canonical = canonical_path(path)
                # Discovery/metadata do not establish decoder support. Only verify file access.
                with open(filesystem_path(canonical), 'rb') as source:
                    source.read(1)
                try:
                    metadata = self.metadata_reader(filesystem_path(path))
                except Exception as error:
                    if path.suffix.lower() not in VIDEO_EXTENSIONS:
                        raise
                    metadata = dict(title=path.stem, artist='', album='', duration=0,
                                    media_type='video')
                    warnings.append(f'{canonical}: Imported with filename metadata; probe failed: {error}. Playback support is unverified.')
                    log.warning('Video metadata unavailable: %s', canonical, exc_info=True)
                metadata['path'] = canonical
                if self.repository.add_track(metadata):
                    added += 1
                else:
                    duplicates += 1
                    skipped += 1
                    reasons.append(f'{canonical}: Already in library')
            except Exception as error:
                errors.append(f'{path}: {error}')
                log.warning('Import failed %s', path, exc_info=True)
            progress(index + 1, len(paths), path.name)
        return dict(added=added, duplicates=duplicates, discovered=discovered, skipped=skipped,
                    failed=len(errors), errors=errors, warnings=warnings, reasons=reasons,
                    pending=len(paths)-processed, cancelled=cancelled())
