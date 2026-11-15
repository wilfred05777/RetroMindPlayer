"""Native QML rendering, pointer/keyboard interactions and live backend bindings."""
import os
from pathlib import Path
import wave
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt, QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest
from retromind.controller import Controller
from retromind.repository import Repository
from retromind.services import ImportService
from test_controller import wait_until


@pytest.fixture
def controls(app):
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda values: warnings.extend(w.toString() for w in values))
    engine.loadData(b'''
import QtQuick
import QtQuick.Controls
ApplicationWindow {
    id: root; visible: true; width: 600; height: 220; color: "#000000"
    property bool playing: false
    MediaSlider { objectName: "seek"; x: 20; y: 20; width: 400; from: 0; to: 1 }
    MediaSlider { objectName: "volume"; x: 20; y: 70; width: 200; from: 0; to: 1 }
    IconButton { objectName: "play"; x: 260; y: 80; prominent: true; iconName: root.playing ? "pause" : "play"; tip: root.playing ? "Pause" : "Play"; onClicked: root.playing = !root.playing }
}
''', QUrl.fromLocalFile(str(Path('retromind/qml/ControlsQA.qml').resolve())))
    assert engine.rootObjects(), warnings
    root = engine.rootObjects()[0]
    root.setScreen(app.primaryScreen())
    root.setPosition(app.primaryScreen().availableGeometry().topLeft() + QPoint(40, 40))
    root.requestActivate()
    assert QTest.qWaitForWindowActive(root, 3000)
    QTest.qWait(150)
    yield root, warnings
    root.close()
    del engine
    app.processEvents()


def shot(root, name):
    folder = os.environ.get('RETROMIND_CONTROLS_QA')
    if folder:
        target = Path(folder)
        target.mkdir(parents=True, exist_ok=True)
        assert root.grabWindow().save(str(target / (name + '.png')))


def test_slider_geometry_pixels_click_drag_and_keyboard(app, controls):
    root, warnings = controls
    for name in ('seek', 'volume'):
        slider = root.findChild(QQuickItem, name)
        track = slider.findChild(QQuickItem, 'sliderTrack')
        fill = slider.findChild(QQuickItem, 'sliderFill')
        handle = slider.findChild(QQuickItem, 'sliderHandle')
        for fraction in (0, .5, 1):
            slider.setProperty('value', fraction)
            QTest.mouseMove(root, QPoint(550, 190))
            QTest.qWait(30)
            assert handle.width() == handle.height() == 12
            assert track.height() == 4
            assert fill.width() == pytest.approx(track.width() * fraction)
            assert handle.x() + handle.width()/2 == pytest.approx(track.x() + fill.width())
            picture = root.grabWindow()
            ratio = picture.width()/root.width()
            def color_at(proportion):
                scene = track.mapToScene(QPointF(track.width()*proportion, 2))
                return picture.pixelColor(round(scene.x()*ratio), round(scene.y()*ratio))
            if fraction > 0:
                assert color_at(.25).red() > 240
            if fraction < 1:
                assert 60 <= color_at(.75).red() <= 85
            shot(root, f'{name}-{int(fraction*100)}')
        slider.setProperty('value', 0)
        start = slider.mapToScene(QPointF(track.x()+track.width()*.25, 16)).toPoint()
        end = slider.mapToScene(QPointF(track.x()+track.width()*.8, 16)).toPoint()
        QTest.mouseClick(root, Qt.LeftButton, pos=start)
        assert slider.property('value') == pytest.approx(.25, abs=.03)
        QTest.mousePress(root, Qt.LeftButton, pos=start)
        QTest.mouseMove(root, end, 50)
        QTest.mouseRelease(root, Qt.LeftButton, pos=end)
        assert slider.property('value') == pytest.approx(.8, abs=.03)
        slider.forceActiveFocus(Qt.TabFocusReason)
        before = slider.property('value')
        QTest.keyClick(root, Qt.Key_Right)
        assert slider.property('value') > before
    assert not warnings, '\n'.join(warnings)


def test_play_pause_states_have_fixed_geometry_and_focus(app, controls):
    root, warnings = controls
    button = root.findChild(QQuickItem, 'play')
    initial = (button.x(), button.y(), button.width(), button.height())
    center = button.mapToScene(QPointF(21,21)).toPoint()
    def surface_red():
        picture = root.grabWindow()
        ratio = picture.width()/root.width()
        point = button.mapToScene(QPointF(21, 4))
        return picture.pixelColor(round(point.x()*ratio), round(point.y()*ratio)).red()
    for playing in (False, True):
        root.setProperty('playing', playing)
        assert button.property('iconName') == ('pause' if playing else 'play')
        assert button.property('tip') == ('Pause' if playing else 'Play')
        QTest.mouseMove(root, QPoint(550,190)); button.setFocus(False)
        QTest.qWait(30)
        assert surface_red() == 255
        shot(root, f'button-{playing}-normal')
        QTest.mouseMove(root, center)
        wait_until(app, lambda: button.property('hovered'))
        assert surface_red() == 229
        shot(root, f'button-{playing}-hover')
        QTest.mousePress(root, Qt.LeftButton, pos=center)
        assert button.property('down')
        QTest.qWait(30)
        assert surface_red() == 197
        shot(root, f'button-{playing}-pressed')
        assert (button.x(),button.y(),button.width(),button.height()) == initial
        QTest.mouseRelease(root, Qt.LeftButton, pos=center)
        assert root.property('playing') != playing
        root.requestActivate()
        assert QTest.qWaitForWindowActive(root, 3000)
        root.findChild(QQuickItem, 'volume').forceActiveFocus()
        QTest.keyClick(root, Qt.Key_Tab)
        QTest.qWait(30)
        assert button.property('visualFocus')
        ring = button.findChild(QQuickItem,'buttonFocusRing')
        assert ring.isVisible()
        shot(root, f'button-{playing}-focus')
        assert (button.x(),button.y(),button.width(),button.height()) == initial
    assert not warnings, '\n'.join(warnings)


def test_bottom_controls_keep_live_playback_bindings(app, tmp_path):
    audio = tmp_path / 'long.wav'
    with wave.open(str(audio),'wb') as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(8000)
        stream.writeframes(b'\0\0' * 8000 * 120)
    repo = Repository(tmp_path / 'library.sqlite3')
    ImportService(repo).import_paths([audio])
    controller = Controller(repo)
    controller.toggleMute()  # Keep actual audio tests silent, even while moving volume.
    engine = QQmlApplicationEngine()
    warnings=[]
    engine.warnings.connect(lambda values: warnings.extend(w.toString() for w in values))
    engine.rootContext().setContextProperty('controller', controller)
    engine.load(QUrl.fromLocalFile(str(Path('retromind/qml/Main.qml').resolve())))
    assert engine.rootObjects(), warnings
    root = engine.rootObjects()[0]
    seek = root.findChild(QQuickItem, 'seekSlider')
    volume = root.findChild(QQuickItem, 'volumeSlider')
    play = root.findChild(QQuickItem, 'playPauseButton')
    try:
        assert not seek.isEnabled()
        assert seek.findChild(QQuickItem, 'sliderHandle').property('color').name() == '#606060'
        controller.playTrack(repo.tracks()[0]['id'])
        wait_until(app, lambda: controller.playing and controller.duration > 0)
        assert seek.isEnabled() and play.property('tip') == 'Pause'
        controller.toggleShuffle(); controller.cycleRepeat(); app.processEvents()
        active_controls = [item for item in root.findChildren(QQuickItem)
                           if item.property('iconName') in ('shuffle','repeat')]
        assert active_controls
        for button in active_controls:
            assert button.property('active')
            assert button.findChild(QQuickItem, 'buttonIcon').property('color').name() == '#1db954'
        for width,height in ((800,600),(1440,900)):
            root.setWidth(width); root.setHeight(height); QTest.qWait(100)
            for item in (seek,volume,play):
                point=item.mapToScene(QPointF(0,0))
                assert point.x() >= 0 and point.y() >= 0
                assert point.x()+item.width() <= root.width()
                assert point.y()+item.height() <= root.height()
            shot(root,f'player-{width}')
        center=play.mapToScene(QPointF(play.width()/2,play.height()/2)).toPoint()
        QTest.mouseClick(root, Qt.LeftButton, pos=center)
        wait_until(app,lambda: not controller.playing)
        assert play.property('tip') == 'Play'
        for item,fraction in ((seek,.5),(volume,.7)):
            track=item.findChild(QQuickItem,'sliderTrack')
            pos=item.mapToScene(QPointF(track.x()+track.width()*fraction,item.height()/2)).toPoint()
            QTest.mouseClick(root,Qt.LeftButton,pos=pos)
        wait_until(app,lambda: abs(controller.position/controller.duration-.5)<.03)
        assert controller.volume == pytest.approx(.7,abs=.03)
        controller.seek(30000); controller.setVolume(.2); app.processEvents()
        assert seek.property('value') == pytest.approx(30000,abs=500)
        assert volume.property('value') == pytest.approx(.2)
        assert not warnings, '\n'.join(warnings)
    finally:
        controller.shutdown(); root.close(); del engine; app.processEvents()
