"""Real Qt integration checks using temporary audio and an isolated database."""
import os
os.environ.setdefault('QT_QUICK_BACKEND', 'software')
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


@pytest.fixture(scope='module')
def app():
    QQuickStyle.setStyle('Basic')
    application = QGuiApplication.instance() or QGuiApplication([])
    yield application


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
        assert not root.grabWindow().isNull()
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
        wait_until(app, lambda: controller._current['id'] == ids[0])
        controller.stop()
        wait_until(app, lambda: not controller.playing)
        controller.setVolume(.35)
        restored = Controller(controller.repo)
        assert restored.volume == pytest.approx(.35)
        assert restored.selectedPlaylist == playlist
        assert not restored.playing
        restored.shutdown()
        (music / 'first.wav').unlink()
        controller.playTrack(ids[0])
        assert 'missing' in controller.status.lower()
        controller.on_error(QMediaPlayer.FormatError, 'Test unsupported codec')
        assert 'codec' in controller.status
        with controller.repo.connect() as db:
            assert db.execute('SELECT count(*) FROM history').fetchone()[0] >= 2
        assert not warnings, warnings
    finally:
        controller.shutdown()
        for root in engine.rootObjects():
            root.close()
        del engine
        app.processEvents()
