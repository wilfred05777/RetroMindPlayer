"""Windows/Qt picture and decoded-audio checks, not subjective A/V sync tests."""
import os
from pathlib import Path
import pytest
from PySide6.QtCore import QUrl, QPointF, Qt
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtTest import QTest
from PySide6.QtMultimedia import QAudioBufferOutput, QMediaPlayer
from retromind.controller import Controller
from retromind.repository import Repository
from retromind.services import ImportService, canonical_path
from media_fixtures import make_video
from test_controller import wait_until, fixture_audio


@pytest.fixture(scope='module')
def video_session(app,tmp_path_factory):
    # Exercise source transitions on the one persistent player, as the app does.
    repo = Repository(tmp_path_factory.mktemp('video-session') / 'library.sqlite3')
    controller = Controller(repo)
    controller.setVolume(0)
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda values: warnings.extend(w.toString() for w in values))
    engine.rootContext().setContextProperty('controller',controller)
    engine.load(QUrl.fromLocalFile(str(Path('retromind/qml/Main.qml').resolve())))
    assert engine.rootObjects(), warnings
    root = engine.rootObjects()[0]
    yield repo,controller,root,warnings
    controller.shutdown()
    root.close()
    del engine
    app.processEvents()


@pytest.mark.parametrize('filename,video_codec,audio_codec', [
    ('h264-aac.mp4','libx264','aac'),
    ('vp9-opus.webm','libvpx-vp9','libopus'),
    ('h264-aac.mkv','libx264','aac'),
    ('hevc-aac.mp4','libx265','aac'),
    ('av1-opus.mkv','libsvtav1','libopus'),
    ('video-only.mp4','libx264',None),
])
def test_real_qt_video_picture_audio_and_fullscreen(app,tmp_path,video_session,filename,video_codec,audio_codec):
    video_path = make_video(tmp_path / filename,video_codec,audio_codec)
    audio_path = tmp_path / 'audio.wav'
    fixture_audio(audio_path)
    repo,controller,root,warnings = video_session
    result = ImportService(repo).import_paths([video_path,audio_path])
    assert not result['errors'], result
    controller.navigate('all')
    if controller.shuffle:
        controller.toggleShuffle()
    while controller.repeat != 'off':
        controller.cycleRepeat()
    if controller.muted:
        controller.toggleMute()
    if not controller.sidebar:
        controller.togglePanel('sidebar')
    frames, audio_buffers = [], []
    sink = controller.playback.player.videoSink()
    def frame_received(frame):
        if frame.isValid():
            image = frame.toImage()
            if not image.isNull():
                frames.append(image)
    sink.videoFrameChanged.connect(frame_received)
    audio_output = QAudioBufferOutput(controller.playback.player)
    audio_output.audioBufferReceived.connect(lambda buffer: audio_buffers.append(buffer.sampleCount()) if buffer.isValid() else None)
    controller.playback.player.setAudioBufferOutput(audio_output)
    try:
        video_id = next(t['id'] for t in repo.tracks() if t['path'] == canonical_path(video_path))
        audio_id = next(t['id'] for t in repo.tracks() if t['path'] == canonical_path(audio_path))
        controller.playTrack(video_id)
        if video_codec == 'libsvtav1':
            wait_until(app,lambda: bool(frames) or 'Cannot play this file' in controller.status)
            if not frames:
                assert 'codec' in controller.status and 'No video frames' in controller.errorDetails
                pytest.xfail('AV1 picture unavailable in this Qt/FFmpeg build; diagnostic handling verified')
        wait_until(app,lambda: bool(frames) and controller.playing)
        assert controller.hasVideo
        assert controller.playback.player.hasAudio() == bool(audio_codec)
        assert (frames[0].width(),frames[0].height()) == (160,96)
        assert frames[0].pixelColor(10,10).red() > 140
        if audio_codec:
            wait_until(app,lambda: any(count > 0 for count in audio_buffers))
        controller.togglePlay()
        wait_until(app,lambda: not controller.playing)
        controller.seek(800)
        wait_until(app,lambda: controller.position >= 750)
        position, source = controller.position, controller.playback.player.source()
        controller.toggleFullscreen()
        wait_until(app,lambda: root.visibility() == QQuickWindow.FullScreen)
        assert controller.playback.player.source() == source
        assert controller.playback.player.videoSink() == sink
        assert abs(controller.position-position) < 80
        QTest.keyClick(root,Qt.Key_Escape)
        wait_until(app,lambda: not controller.fullscreen)
        assert abs(controller.position-position) < 80
        output = root.findChild(type(root.contentItem()),'mainVideoOutput')
        if output is None:
            from PySide6.QtQuick import QQuickItem
            output = root.findChild(QQuickItem,'mainVideoOutput')
        assert output is not None
        point = output.mapToScene(QPointF(output.width()/2,output.height()/2)).toPoint()
        QTest.qWait(100)
        QTest.mouseDClick(root,Qt.LeftButton,pos=point)
        wait_until(app,lambda: controller.fullscreen)
        controller.exitFullscreen()
        QTest.qWait(200)
        app.processEvents()
        assert abs(output.property('contentRect').width() / output.property('contentRect').height()-160/96) < .02
        # Render browsing views while the paused video and same decoder remain attached.
        controller.navigate('home'); app.processEvents()
        controller.navigate('all'); controller.togglePanel('grid'); app.processEvents()
        controller.togglePanel('grid'); app.processEvents()
        root.setProperty('queueTab', True); app.processEvents()
        root.setWidth(800); root.setHeight(600); app.processEvents()
        root.setWidth(1440); root.setHeight(900); app.processEvents()
        QTest.qWait(200)
        picture = root.grabWindow()
        center = output.mapToScene(QPointF(output.width()/2,output.height()/2))
        ratio = picture.width()/root.width()
        assert picture.pixelColor(int(center.x()*ratio),int(center.y()*ratio)).green() > 100, 'Paused video disappeared after fullscreen/browsing/resize'
        if filename == 'h264-aac.mp4' and os.environ.get('RETROMIND_QA_SCREENSHOT'):
            picture.save(os.environ['RETROMIND_QA_SCREENSHOT'])
        assert not warnings, '\n'.join(warnings)
        controller.playTrack(audio_id)
        wait_until(app,lambda: controller.playing and not controller.hasVideo)
        assert not sink.videoFrame().isValid()  # No stale frame over audio.
        controller.toggleShuffle()
        controller.cycleRepeat()
        controller.toggleMute()
        controller.togglePanel('sidebar')
        controller.saveWindow(1000,720)
        controller.savePanelWidths(220,280)
        restored = Controller(repo)
        assert restored.shuffle and restored.repeat == 'all' and restored.muted
        assert not restored.sidebar and restored.windowWidth == 1000
        assert restored.sidebarWidth == 220 and restored.rightWidth == 280
        assert not restored.playing
        restored.shutdown()
    finally:
        controller.stop()
        controller.playback.player.setSource(QUrl())
        controller.playback.player.setAudioBufferOutput(None)
        sink.videoFrameChanged.disconnect(frame_received)
        audio_output.deleteLater()
        app.processEvents()
