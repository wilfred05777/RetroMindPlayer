"""Use PyInstaller Qt dependency discovery, limited to this app's QML modules."""
from pathlib import PurePosixPath
from PyInstaller.utils.hooks.qt import add_qt6_dependencies, pyside6_library_info

hiddenimports, binaries, datas = add_qt6_dependencies(__file__)
qml_binaries, qml_datas = pyside6_library_info.collect_qtqml_files()

def used(item):
    destination = str(item[1]).replace('\\', '/')
    if '/qml/' not in destination:
        return True
    module = destination.split('/qml/', 1)[1]
    if module.startswith(('QtQuick/Pdf', 'QtQuick/Scene2D', 'QtQuick/Scene3D', 'QtQuick/VirtualKeyboard')):
        return False
    return module.split('/')[0] in ('QtCore', 'QtQml', 'QtQuick', 'QtMultimedia') or module.startswith(('Qt/labs/folderlistmodel', 'Qt/labs/platform', 'Qt/labs/settings', 'Qt/labs/qmlmodels'))

binaries += [item for item in qml_binaries if used(item)]
datas += [item for item in qml_datas if used(item)]
