"""Explicit, isolated frozen-build diagnostic; never runs during normal startup."""
import json
from pathlib import Path
import sys
import time
from PySide6.QtCore import QUrl
from PySide6.QtGui import QWindow
from PySide6.QtMultimedia import QAudioBufferOutput


def run(app, engine, controller, directory, qml_warnings):
    directory = Path(directory).resolve()
    report = dict(frozen=bool(getattr(sys, 'frozen', False)), executable=sys.executable,
                  working_directory=str(Path.cwd()), checks=[], failures=[])
    def check(name, condition=True):
        if not condition:
            raise AssertionError(name)
        report['checks'].append(name)
    def wait(condition, timeout=15):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            app.processEvents()
            if condition():
                return
            time.sleep(.01)
        raise AssertionError('Timed out: ' + controller.status)
    try:
        check('QML root loaded', bool(engine.rootObjects()))
        root = engine.rootObjects()[0]
        controller.setVolume(0)
        if not controller.muted:
            controller.toggleMute()
        check('Application icon decoded', not app.windowIcon().pixmap(64,64).isNull())
        check('Startup silent', not controller.playing)
        controller.previewFolder(QUrl.fromLocalFile(str(directory/'fixtures')).toString())
        wait(lambda: not controller.busy)
        check('Recursive discovery', controller._preview_report.get('discovered', 0) >= 3)
        controller.importDiscovered()
        wait(lambda: not controller.busy)
        check('Library import', len(controller.repo.tracks()) >= 3)
        report['import_status'] = controller.status
        report['import_details'] = controller.errorDetails
        count = len(controller.repo.tracks())
        controller.importDiscovered()
        wait(lambda: not controller.busy)
        check('Duplicate imports preserve count', len(controller.repo.tracks()) == count)
        controller.navigate('all')
        tracks = controller.repo.tracks()
        video = next(row for row in tracks if Path(row['path']).name == 'h264-aac.mp4')
        art = {}
        controller.artworkReady.connect(lambda track_id, url: art.update({track_id:url}))
        controller.requestArtwork(video['id'])
        wait(lambda: video['id'] in art)
        check('Background thumbnail/cached artwork', bool(art[video['id']]))
        frames, samples = [], []
        sink = controller.playback.player.videoSink()
        check('QML VideoOutput attached', sink is not None)
        sink.videoFrameChanged.connect(lambda frame: frames.append((frame.width(),frame.height())) if frame.isValid() else None)
        audio = QAudioBufferOutput(controller.playback.player)
        audio.audioBufferReceived.connect(lambda buffer: samples.append(buffer.sampleCount()) if buffer.isValid() else None)
        controller.playback.player.setAudioBufferOutput(audio)
        for filename in ('tone.wav','h264-aac.mp4','vp9-opus.webm','tone.wav'):
            frames.clear(); samples.clear()
            row = next(row for row in tracks if Path(row['path']).name == filename)
            controller.playTrack(row['id'])
            wait(lambda: controller.playing and controller.duration > 0 and any(samples))
            if row['media_type'] == 'video':
                wait(lambda: bool(frames))
                check(filename + ': decoded video', frames[0] == (160,96))
            else:
                check('Audio transition clears video', not controller.hasVideo and not sink.videoFrame().isValid())
            check(filename + ': decoded audio buffers')
            controller.togglePlay(); wait(lambda: not controller.playing)
            controller.seek(800); wait(lambda: controller.position >= 750)
            check(filename + ': pause and seek')
            if row['media_type'] == 'video':
                source, position = controller.playback.player.source(), controller.position
                controller.toggleFullscreen()
                wait(lambda: root.visibility() == QWindow.FullScreen)
                controller.exitFullscreen()
                wait(lambda: root.visibility() != QWindow.FullScreen)
                check(filename + ': fullscreen preserves source/position', controller.playback.player.source() == source and abs(controller.position-position) < 100)
        controller.setVolume(.37)
        check('Volume binding', abs(controller.volume-.37) < .001)
        playlist = next((p['id'] for p in controller.repo.playlists() if p['name'] == 'Packaging verification'), None)
        if playlist is None:
            playlist = controller.repo.create_playlist('Packaging verification')
        for track in tracks:
            controller.repo.add_to_playlist(playlist, track['id'])
        controller.repo.favourite(video['id'])
        controller.repo.save_setting('packaging-sentinel', '0.1.0-beta-preserve')
        check('Persistent playlist/settings', controller.repo.setting('packaging-sentinel') == '0.1.0-beta-preserve' and len(controller.repo.tracks(playlist_id=playlist)) == count)
        root.grabWindow().save(str(directory/'packaged-ui.png'))
        check('No QML runtime warnings', not qml_warnings)
        report['qml_warnings'] = qml_warnings
        report['data_path'] = controller.repo.path
        report['success'] = True
    except Exception as error:
        report['success'] = False
        report['failures'].append(str(error))
        report['status'] = controller.status
        report['details'] = controller.errorDetails
    finally:
        controller.shutdown()
        (directory/'package-test-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        app.exit(0 if report['success'] else 1)
