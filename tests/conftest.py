import os
os.environ.setdefault('QSG_RHI_PREFER_SOFTWARE_RENDERER', '1')
os.environ.setdefault('QT_MEDIA_BACKEND', 'ffmpeg')
os.environ.setdefault('QT_FFMPEG_DECODING_HW_DEVICE_TYPES', ',')
import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuickControls2 import QQuickStyle


@pytest.fixture(scope='session')
def app():
    QQuickStyle.setStyle('Basic')
    application = QGuiApplication.instance() or QGuiApplication([])
    yield application
