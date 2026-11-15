# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import PySide6
from PyInstaller.utils.hooks import collect_submodules

root = Path(SPECPATH).parent
qt = Path(PySide6.__file__).parent
# Explicit application-data allowlist: never collect the workspace or user-data tree.
datas = [(str(p), 'retromind/qml') for p in (root/'retromind/qml').glob('*.qml')]
datas += [(str(p), 'retromind/assets') for p in (root/'retromind/assets').glob('*') if p.suffix in ('.ico','.png','.svg')]
datas += [(str(root/'packaging/licenses'), 'licenses'), (str(root/'packaging/THIRD_PARTY_NOTICES.md'), '.'),
          (str(root/'packaging/RELEASE_NOTES.md'), '.'), (str(root/'packaging/CLEAN_MACHINE_CHECKLIST.md'), '.')]
datas += [(str(root/'packaging/generated/build-info.json'), '.')]
# Qt playback and PyAV probing have different FFmpeg ABI versions. Keep both.
binaries = [(str(p), 'PySide6') for p in qt.glob('*.dll') if p.name.startswith(('avcodec-', 'avformat-', 'avutil-', 'swscale-', 'swresample-'))]
a = Analysis([str(root/'packaging/launcher.py')], pathex=[str(root)],
    binaries=binaries, datas=datas,
    hiddenimports=collect_submodules('mutagen', filter=lambda name: not name.startswith('mutagen._tools')) + ['PySide6.QtMultimedia', 'PySide6.QtQuick', 'PySide6.QtQml', 'PySide6.QtQuickControls2'],
    hookspath=[str(root/'packaging/hooks')],
    excludes=['pytest','unittest','tkinter','pip','setuptools','PyQt5','PyQt6','PySide2',
              'PySide6.QtWebEngineCore','PySide6.QtWebEngineQuick','PySide6.QtWebEngineWidgets',
              'PySide6.QtPdf','PySide6.QtPdfWidgets','PySide6.Qt3DCore','PySide6.QtQuick3D'],
    noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='RetroMindPlayer',
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=False, disable_windowed_traceback=False,
    icon=str(root/'retromind/assets/retromind.ico'),
    version=str(root/'packaging/generated/version-info.txt'),
    manifest=str(root/'packaging/windows.manifest'), uac_admin=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='RetroMindPlayer')
