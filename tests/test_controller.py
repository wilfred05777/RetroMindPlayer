"""Real Qt integration checks using temporary audio and an isolated database."""
import os
os.environ.setdefault('QSG_RHI_PREFER_SOFTWARE_RENDERER', '1')
import time
import wave
from pathlib import Path
import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtQuickControls2 import QQuickStyle
from retromind.controller import Controller
from retromind.repository import Repository


def wait_until(app, condition, timeout=6):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return
        time.sleep(.01)
    assert condition(), 'Timed out waiting for Qt integration condition'


def fixture_audio(path):
    with wave.open(str(path), 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b'\x00\x00' * 16000)


def test_qml_worker_playback_and_missing_file(app, tmp_path):
    music = tmp_path / 'music'
    music.mkdir()
    for name in ('first.wav', 'second.wav'):
        fixture_audio(music / name)
    controller = Controller(Repository(tmp_path / 'library.sqlite3'))
    controller.setVolume(0)  # Integration checks never emit sound.
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    engine.rootContext().setContextProperty('controller', controller)
    engine.load(QUrl.fromLocalFile(str(Path('retromind/qml/Main.qml').resolve())))
    try:
        assert engine.rootObjects()
        root = engine.rootObjects()[0]
        assert not controller.playing  # Startup is silent.
        controller.importFolder(QUrl.fromLocalFile(str(music)).toString())
        wait_until(app, lambda: not controller.busy)
        assert len(controller.tracks) == 2
        ids = [t['id'] for t in controller.tracks]
        controller.createPlaylist('Integration playlist')
        playlist = controller.selectedPlaylist
        for track_id in reversed(ids):
            controller.addToPlaylist(track_id, playlist)
        assert [t['id'] for t in controller.tracks] == list(reversed(ids))
        wait_until(app, lambda: root.isVisible())
        app.processEvents()
        image = root.grabWindow()
        assert not image.isNull()
        if os.environ.get('RETROMIND_QA_SCREENSHOT'):
            image.save(os.environ['RETROMIND_QA_SCREENSHOT'])
        # Exercise a populated library and QML bindings before playing.
        assert not warnings, warnings
        controller.playTrack(ids[1])
        wait_until(app, lambda: controller.playing and controller.duration > 0)
        controller.togglePlay()
        wait_until(app, lambda: controller.playback.player.playbackState() == QMediaPlayer.PausedState)
        controller.seek(500)
        wait_until(app, lambda: controller.position >= 450)
        controller.togglePlay()
        wait_until(app, lambda: controller.playing)
        controller.seek(controller.duration - 100)
        wait_until(app, lambda: controller._current['id'] == ids[0] and controller._recorded and controller.playing)
        controller.stop()
        wait_until(app, lambda: not controller.playing)
        controller.setVolume(.35)
        restored = Controller(controller.repo)
        assert restored.volume == pytest.approx(.35)
        assert restored.selectedPlaylist == playlist
        assert not restored.playing
        restored.shutdown()
        controller.repo.add_track(dict(path=str(music / 'absent.wav'), title='Missing file', artist='', album='', duration=0))
        missing_id = controller.repo.tracks('Missing file')[0]['id']
        controller.playTrack(missing_id)
        assert 'missing' in controller.status.lower()
        invalid = music / 'corrupt.mp3'
        invalid.write_bytes(b'not a music file')
        controller.repo.add_track(dict(path=str(invalid), title='Corrupt file', artist='', album='', duration=0))
        invalid_id = controller.repo.tracks('Corrupt file')[0]['id']
        controller.playTrack(invalid_id)
        wait_until(app, lambda: 'Cannot play this file' in controller.status)
        assert 'codecs' in controller.status
        with controller.repo.connect() as db:
            assert db.execute('SELECT count(*) FROM history').fetchone()[0] >= 2
        assert not warnings, warnings
    finally:
        controller.shutdown()
        for root in engine.rootObjects():
            root.close()
        del engine
        app.processEvents()


def test_automatic_queue_skips_missing_and_corrupt_media(app,tmp_path):
    valid = tmp_path / 'valid.wav'
    fixture_audio(valid)
    corrupt = tmp_path / 'corrupt.mp3'
    corrupt.write_bytes(b'not audio')
    repo = Repository(tmp_path / 'skip.sqlite3')
    for title,path in [('A start',valid),('B missing',tmp_path / 'absent.wav'),('C corrupt',corrupt),('D finish',valid)]:
        # Distinct paths for the two valid entries.
        if title == 'D finish':
            path = tmp_path / 'finish.wav'
            fixture_audio(path)
        repo.add_track(dict(path=str(path),title=title,artist='',album='',duration=2))
    controller = Controller(repo)
    controller.setVolume(0)
    try:
        first,last = controller.tracks[0]['id'],controller.tracks[-1]['id']
        controller.playTrack(first)
        wait_until(app,lambda: controller.playing and controller.duration > 0)
        controller.seek(controller.duration-100)
        wait_until(app,lambda: controller._current['id'] == last and controller.playing)
        assert 'corrupt.mp3' in controller.errorDetails
    finally:
        controller.shutdown()


def test_large_library_virtualizes_rows_and_lazy_artwork(app,tmp_path):
    from PySide6.QtCore import QMetaObject
    from PySide6.QtQuick import QQuickItem
    repo = Repository(tmp_path / 'large.sqlite3')
    with repo.connect() as db:
        db.executemany('INSERT INTO tracks(path,title) VALUES(?,?)',
                       [(str(tmp_path / f'{i}.wav'),f'Track {i:05}') for i in range(10000)])
    controller = Controller(repo)
    controller.navigate('all')
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty('controller',controller)
    engine.load(QUrl.fromLocalFile(str(Path('retromind/qml/Main.qml').resolve())))
    root = engine.rootObjects()[0]
    try:
        app.processEvents()
        view = root.findChild(QQuickItem,'libraryList')
        assert view.property('count') == 10000
        assert QMetaObject.invokeMethod(view,'positionViewAtEnd')
        wait_until(app,lambda: view.property('contentY') > 500000)
        assert len(controller.artwork.pending) + len(controller.artwork.results) < 100
    finally:
        controller.shutdown()
        root.close()
        del engine
        app.processEvents()

def test_folder_picker_preview_shows_mp4_and_recursive_import(app, tmp_path):
    from pathlib import Path
    from PySide6.QtCore import QUrl, QObject, QMetaObject, Q_ARG
    from PySide6.QtQml import QQmlApplicationEngine
    from media_fixtures import make_video
    from retromind.services import ImportService
    root_path = tmp_path / "O'Brien course \u97f3\u4e50 \u2013 zero to hero"
    root_path.mkdir()
    make_video(root_path / 'lesson.MP4', audio_codec=None)
    nested = root_path / 'nested'
    nested.mkdir()
    fixture_audio(nested / 'audio.wav')
    repo = Repository(tmp_path / 'preview.sqlite3')
    controller = Controller(repo)
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda values: warnings.extend(w.toString() for w in values))
    engine.rootContext().setContextProperty('controller', controller)
    engine.load(QUrl.fromLocalFile(str(Path('retromind/qml/Main.qml').resolve())))
    assert engine.rootObjects(), warnings
    root = engine.rootObjects()[0]
    try:
        from PySide6.QtQuick import QQuickItem
        preview = root.findChild(QQuickItem, 'importPreviewList')
        controller.previewFolder('')
        assert not controller.busy
        picker = root.findChild(QObject, 'nativeImportFolderPicker')
        assert picker.property('title') == 'Select a folder; files will appear in the next preview.'
        dialog = root.findChild(QObject, 'folderImportDialog')
        assert QMetaObject.invokeMethod(dialog, 'previewFolderSelection', Q_ARG(QUrl, QUrl.fromLocalFile(str(root_path))))
        assert Path(controller.worker.sources) == root_path
        wait_until(app, lambda: not controller.busy)
        assert len(controller.importPreview) == 2
        assert any('nested' in entry['name'] for entry in controller.importPreview)
        assert preview.property('count') == 2
        assert repo.tracks() == []  # Discovery alone never inserts records.
        app.processEvents()
        import os
        if os.environ.get('RETROMIND_IMPORT_SCREENSHOT'):
            root.grabWindow().save(os.environ['RETROMIND_IMPORT_SCREENSHOT'])
        dialog = root.findChild(QObject, 'folderImportDialog')
        QMetaObject.invokeMethod(dialog, 'importRequested')
        wait_until(app, lambda: not controller.busy)
        assert '2 imported' in controller.status
        file_dialog = root.findChild(QObject, 'openMediaFilesDialog')
        filters = file_dialog.property('nameFilters')
        assert '*.mp4' in filters[0] and '*.MP4' in filters[0]
        assert filters[-1] == 'All files (*)'
        controller.importFiles([QUrl.fromLocalFile(str(root_path / 'lesson.MP4'))])
        wait_until(app, lambda: not controller.busy)
        assert '1 skipped' in controller.status and 'Already in library' in controller.errorDetails
        assert len(repo.tracks(media_type='video')) == 1
        assert len(repo.tracks(media_type='audio')) == 1
        assert not warnings, '\n'.join(warnings)
    finally:
        controller.shutdown()
        root.close()
        del engine
        app.processEvents()
