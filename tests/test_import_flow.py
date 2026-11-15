"""Discovery and import are independent of metadata/thumbnail decode success."""
import os
from pathlib import Path
import pytest
from retromind.services import ImportService, canonical_path, filesystem_path
from retromind.repository import Repository
from media_fixtures import make_video


def test_recursive_discovery_preview_import_and_reasons(tmp_path):
    root = tmp_path / "O'Brien music \u97f3\u4e50 \u2013 course"
    nested = root / 'nested lessons'
    nested.mkdir(parents=True)
    make_video(nested / 'Lesson.MP4', audio_codec=None)
    (root / 'bad metadata.mp4').write_bytes(b'unprobeable video')
    (root / 'notes.txt').write_text('ignored')
    repo = Repository(tmp_path / 'library.sqlite3')
    service = ImportService(repo)
    discovery = service.discover(root)
    assert discovery['discovered'] == 2 and discovery['skipped'] == 1
    assert len(discovery['entries']) == 3
    assert any(e['name'].endswith('Lesson.MP4') and 'nested' in e['name'] for e in discovery['entries'])
    assert repo.tracks() == []
    first = service.import_paths(discovery['paths'], discovery=discovery)
    assert (first['added'], first['skipped'], first['failed']) == (2, 1, 0)
    assert len(first['warnings']) == 1 and 'probe failed' in first['warnings'][0]
    fallback = next(t for t in repo.tracks() if t['title'] == 'bad metadata')
    assert fallback['media_type'] == 'video' and fallback['width'] is None
    assert fallback['video_codec'] is None and fallback['has_video'] is None
    second = service.import_paths(discovery['paths'], discovery=discovery)
    assert (second['added'], second['duplicates'], second['skipped']) == (0, 2, 3)
    assert any('Already in library' in reason for reason in second['reasons'])
    assert any('Unsupported extension' in reason for reason in second['reasons'])


def test_removed_unreadable_and_unsupported_files_have_reasons(tmp_path, monkeypatch):
    import builtins
    missing = tmp_path / 'gone.mp4'
    denied = tmp_path / 'denied.MP4'
    denied.write_bytes(b'video')
    original_open = builtins.open
    def checked_open(path, *args, **kwargs):
        if os.path.normcase(str(path)) == os.path.normcase(str(denied)):
            raise PermissionError('Access denied for test')
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(builtins, 'open', checked_open)
    service = ImportService(Repository(tmp_path / 'library.sqlite3'))
    result = service.import_paths([missing, denied, tmp_path / 'notes.txt'])
    assert (result['discovered'], result['added'], result['skipped'], result['failed']) == (2, 0, 1, 2)
    assert any('gone.mp4' in reason for reason in result['errors'])
    assert any('Access denied' in reason for reason in result['errors'])
    assert 'Unsupported extension' in result['reasons'][0]


def test_windows_long_path_import_and_duplicate_identity(tmp_path):
    folder = tmp_path / "User's \u97f3\u4e50"
    while len(str(folder)) < 320:
        folder /= 'long folder segment with spaces'
    Path(filesystem_path(folder)).mkdir(parents=True)
    path = folder / 'Course.MP4'
    make_video(Path(filesystem_path(path)), audio_codec=None)
    repo = Repository(tmp_path / 'library.sqlite3')
    service = ImportService(repo)
    report = service.discover(tmp_path / "User's \u97f3\u4e50")
    assert report['discovered'] == 1
    result = service.import_paths(report['paths'], discovery=report)
    assert (result['added'], result['failed'], result['warnings']) == (1, 0, [])
    track, = repo.tracks()
    assert track['path'] == canonical_path(path)
    assert not track['path'].startswith('\\\\?\\')
    assert track['width'] == 160
    assert service.import_paths([filesystem_path(path)])['duplicates'] == 1


def test_thumbnail_failure_cannot_remove_imported_mp4(tmp_path, monkeypatch):
    from retromind import artwork
    video = make_video(tmp_path / 'video.mp4', audio_codec=None)
    repo = Repository(tmp_path / 'library.sqlite3')
    assert ImportService(repo).import_paths([video])['added'] == 1
    def fail(_):
        raise RuntimeError('Thumbnail decoder failed')
    monkeypatch.setattr(artwork, 'image_for_media', fail)
    emitted = []
    class Signal:
        def emit(self, *args):
            emitted.append(args)
    class Signals:
        ready = Signal()
    track, = repo.tracks()
    artwork.ArtworkTask(track['id'], track['path'], tmp_path, Signals()).run()
    assert emitted and emitted[0][2] == ''
    assert repo.track(track['id'])['path'] == track['path']


def test_discovery_errors_and_cancellation_are_visible(tmp_path, monkeypatch):
    from retromind import services
    def walk(root, onerror):
        onerror(PermissionError(13, 'Access denied', str(root / 'private')))
        yield str(root), [], ['one.MP4', 'ignore.txt']
    monkeypatch.setattr(services.os, 'walk', walk)
    service = ImportService(Repository(tmp_path / 'library.sqlite3'))
    report = service.discover(tmp_path)
    assert report['discovered'] == 1 and report['skipped'] == 1
    assert 'private' in report['errors'][0]
    report = service.discover(tmp_path, cancelled=lambda: True)
    assert report['cancelled'] and not report['paths']
