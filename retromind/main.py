import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import os
from PySide6.QtCore import QStandardPaths, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from .controller import Controller
from .repository import Repository


def main():
    os.environ.setdefault('QT_QUICK_BACKEND', 'software')
    QQuickStyle.setStyle('Basic')
    app = QGuiApplication(sys.argv)
    app.setOrganizationName('RetroMind')
    app.setApplicationName('RetroMindPlayer')
    app.setApplicationDisplayName('RetroMind Player')
    data = Path(QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation))
    data.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, handlers=[
        RotatingFileHandler(data / 'retromind.log', maxBytes=2_000_000, backupCount=2, encoding='utf-8'),
        logging.StreamHandler()], format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    controller = Controller(Repository(data / 'library.sqlite3'))
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty('controller', controller)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / 'qml' / 'Main.qml')))
    if not engine.rootObjects():
        return 1
    app.aboutToQuit.connect(controller.shutdown)
    if '--smoke-test' in sys.argv:
        QTimer.singleShot(2000, app.quit)
    result = app.exec()
    # Destroy QML objects while their context object is still alive.
    del engine
    return result


if __name__ == '__main__':
    raise SystemExit(main())
