import argparse
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import os
from PySide6.QtCore import QStandardPaths, QTimer, QUrl
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from .controller import Controller
from .repository import Repository
from . import __version__, DISPLAY_VERSION
from .instance import coordinate


def main():
    # Use Direct3D WARP software rendering on Windows: VideoOutput stays available
    # without relying on AMD GPU decoding. Respect explicit user overrides.
    os.environ.setdefault('QSG_RHI_PREFER_SOFTWARE_RENDERER', '1')
    os.environ.setdefault('QT_MEDIA_BACKEND', 'ffmpeg')
    os.environ.setdefault('QT_FFMPEG_DECODING_HW_DEVICE_TYPES', ',')
    parser = argparse.ArgumentParser(description='RetroMind Player')
    parser.add_argument('--quit-for-update', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--smoke-test', action='store_true')
    parser.add_argument('--data-dir', type=Path, help='Explicit alternate user-data directory for isolated testing')
    parser.add_argument('--package-test', type=Path, help='Run isolated diagnostics using fixtures in this directory')
    args, _ = parser.parse_known_args()
    QQuickStyle.setStyle('Basic')
    app = QGuiApplication(sys.argv)
    app.setOrganizationName('RetroMind')
    app.setApplicationName('RetroMindPlayer')
    app.setApplicationVersion(__version__)
    app.setApplicationDisplayName('RetroMind Player ' + DISPLAY_VERSION)
    app.setWindowIcon(QIcon(str(Path(__file__).parent / 'assets' / 'retromind.ico')))
    roots = []
    instance_server, previous_exit = coordinate(app, lambda: roots[0] if roots else None, args.quit_for_update)
    if previous_exit is not None:
        return previous_exit
    data = ((args.package_test.resolve() / 'userdata') if args.package_test else args.data_dir.resolve() if args.data_dir else Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)))
    data.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, handlers=[
        RotatingFileHandler(data / 'retromind.log', maxBytes=2_000_000, backupCount=2, encoding='utf-8'),
        logging.StreamHandler()], format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    controller = Controller(Repository(data / 'library.sqlite3'))
    engine = QQmlApplicationEngine()
    qml_warnings = []
    engine.warnings.connect(lambda values: qml_warnings.extend(value.toString() for value in values))
    engine.rootContext().setContextProperty('controller', controller)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / 'qml' / 'Main.qml')))
    if not engine.rootObjects():
        return 1
    roots.extend(engine.rootObjects())
    app.aboutToQuit.connect(controller.shutdown)
    if args.package_test:
        from .diagnostics import run
        args.package_test.resolve().mkdir(parents=True, exist_ok=True)
        QTimer.singleShot(0, lambda: run(app, engine, controller, args.package_test, qml_warnings))
    elif args.smoke_test:
        QTimer.singleShot(2000, app.quit)
    result = app.exec()
    # Destroy QML objects while their context object is still alive.
    roots.clear()
    del engine
    instance_server.close()
    return result


if __name__ == '__main__':
    raise SystemExit(main())
