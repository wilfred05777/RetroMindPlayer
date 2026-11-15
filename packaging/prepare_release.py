"""Generate original icon, version resources and bundled third-party notices."""
from pathlib import Path
import importlib.metadata as metadata
import json
import shutil
import struct
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'packaging'
LICENSES = PACK / 'licenses'
GENERATED = PACK / 'generated'


def download(item):
    name, url = item
    target = LICENSES / name
    if not target.exists():
        request = urllib.request.Request(url, headers={'User-Agent': 'RetroMind-Local-Build/0.1'})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                content = response.read()
        except Exception as error:
            raise RuntimeError(f'License download failed: {url}') from error
        target.write_bytes(content)
    return name


def icon():
    image = QImage(256, 256, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor('#121212'))
    painter.drawRoundedRect(QRectF(0, 0, 256, 256), 52, 52)
    painter.setPen(QPen(QColor('#1DB954'), 14))
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(QRectF(37, 37, 182, 182))
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor('#FFFFFF'))
    triangle = QPainterPath()
    triangle.moveTo(106, 77); triangle.lineTo(180, 128); triangle.lineTo(106, 179); triangle.closeSubpath()
    painter.drawPath(triangle)
    painter.end()
    assets = ROOT / 'retromind/assets'
    assets.mkdir(exist_ok=True)
    image.save(str(assets / 'retromind.png'))
    sizes = (16, 24, 32, 48, 64, 128, 256)
    chunks = []
    for size in sizes:
        data = QByteArray()
        buffer = QBuffer(data); buffer.open(QIODevice.WriteOnly)
        image.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation).save(buffer, 'PNG')
        chunks.append(bytes(data))
    offset = 6 + len(sizes)*16
    directory = []
    for size, data in zip(sizes, chunks):
        directory.append(struct.pack('<BBBBHHII', size % 256, size % 256, 0, 0, 1, 32, len(data), offset))
        offset += len(data)
    (assets / 'retromind.ico').write_bytes(struct.pack('<HHH', 0, 1, len(sizes)) + b''.join(directory) + b''.join(chunks))


def main():
    LICENSES.mkdir(exist_ok=True); GENERATED.mkdir(exist_ok=True)
    release = json.loads((PACK/'release.json').read_text())
    import retromind
    assert retromind.__version__ == release['python_version']
    icon()
    packages = ('av', 'mutagen', 'PySide6', 'PySide6_Essentials', 'PySide6_Addons', 'shiboken6', 'pyinstaller')
    records = []
    for name in packages:
        dist = metadata.distribution(name)
        records.append(dict(name=name, version=dist.version, license=dist.metadata.get('License-Expression') or dist.metadata.get('License')))
        destination = LICENSES / name
        destination.mkdir(exist_ok=True)
        for file in dist.files or []:
            if ('licenses/' in str(file).lower() or str(file).endswith('COPYING.txt')) and Path(file).suffix.lower() in ('.txt','.rst','.md',''):
                source = Path(dist.locate_file(file))
                if source.is_file():
                    shutil.copy2(source, destination / source.name)
    shutil.copy2(Path(sys.base_prefix)/'LICENSE.txt', LICENSES/'Python-LICENSE.txt')
    urls = {
        'GPL-2.0.txt': 'https://www.gnu.org/licenses/old-licenses/gpl-2.0.txt',
        'GPL-3.0.txt': 'https://www.gnu.org/licenses/gpl-3.0.txt',
        'LGPL-3.0.txt': 'https://www.gnu.org/licenses/lgpl-3.0.txt',
        'LGPL-2.1.txt': 'https://www.gnu.org/licenses/old-licenses/lgpl-2.1.txt',
        'LGPL-2.0.txt': 'https://www.gnu.org/licenses/old-licenses/lgpl-2.0.txt',
        'GCC-Runtime-Exception-3.1.html': 'https://www.gnu.org/licenses/gcc-exception-3.1.html',
        'OpenSSL-LICENSE.txt': 'https://raw.githubusercontent.com/openssl/openssl/openssl-3.5.7/LICENSE.txt',
        'MSVC-runtime-license.html': 'https://visualstudio.microsoft.com/license-terms/vs2022-cruntime/',
        'winpthreads-COPYING.txt': 'https://raw.githubusercontent.com/mingw-w64/mingw-w64/master/mingw-w64-libraries/winpthreads/COPYING',
        'Apache-2.0.txt': 'https://www.apache.org/licenses/LICENSE-2.0.txt',
        'dav1d-COPYING.txt': 'https://raw.githubusercontent.com/videolan/dav1d/master/COPYING',
        'libopus-COPYING.txt': 'https://raw.githubusercontent.com/xiph/opus/main/COPYING',
        'libvpx-LICENSE.txt': 'https://raw.githubusercontent.com/webmproject/libvpx/main/LICENSE',
        'libvpx-PATENTS.txt': 'https://raw.githubusercontent.com/webmproject/libvpx/main/PATENTS',
        'libwebp-COPYING.txt': 'https://raw.githubusercontent.com/webmproject/libwebp/main/COPYING',
        'oneVPL-LICENSE.txt': 'https://raw.githubusercontent.com/intel/libvpl/main/LICENSE',
        'SVT-AV1-LICENSE.txt': 'https://gitlab.com/AOMediaCodec/SVT-AV1/-/raw/master/LICENSE.md',
        'SVT-AV1-PATENTS.txt': 'https://gitlab.com/AOMediaCodec/SVT-AV1/-/raw/master/PATENTS.md',
        'MinGW-runtime-COPYING.txt': 'https://raw.githubusercontent.com/mingw-w64/mingw-w64/master/COPYING',
        'zlib-LICENSE.txt': 'https://raw.githubusercontent.com/madler/zlib/develop/LICENSE',
    }
    # Keep official, complete license/attribution pages for the shipped Qt modules.
    import re
    cached_manifest = LICENSES/'download-sources.json'
    cached_qt = {name:url for name,url in json.loads(cached_manifest.read_text()).items() if name.startswith('Qt-')} if cached_manifest.exists() else {}
    if cached_qt:
        urls.update(cached_qt)
    else:
        for module in ('qtcore','qtgui','qtnetwork','qtqml','qtquick','qtquickcontrols','qtmultimedia','qtsvg','qtopengl'):
            url = f'https://doc.qt.io/qt-6.12/{module}-index.html'
            try:
                with urllib.request.urlopen(url, timeout=40) as response:
                    html = response.read().decode()
                for page in set(re.findall(r'href="([^"/#]*-attribution-[^"/#]+\.html)"', html)):
                    urls['Qt-' + page] = 'https://doc.qt.io/qt-6.12/' + page
            except Exception as error:
                raise RuntimeError(f'Cannot obtain Qt attribution index: {url}') from error
    print('Collecting licence files:',len(urls), flush=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(download, urls.items()))
    (LICENSES/'download-sources.json').write_text(json.dumps(urls,indent=2),encoding='utf-8')
    import av
    info = dict(release=release, python=sys.version.split()[0], packages=records,
                pyav_ffmpeg=av._core.library_meta, qt_version=__import__('PySide6').__version__,
                playback='Qt Multimedia / bundled FFmpeg; PyAV is metadata and artwork only')
    (GENERATED/'build-info.json').write_text(json.dumps(info,indent=2),encoding='utf-8')
    version_text = '''VSVersionInfo(ffi=FixedFileInfo(filevers=(0,1,1,0), prodvers=(0,1,1,0), mask=0x3f, flags=0x2, OS=0x40004, fileType=0x1, subtype=0x0, date=(0,0)), kids=[StringFileInfo([StringTable('040904B0', [StringStruct('CompanyName','Wilfred Bancairen'), StringStruct('FileDescription','RetroMind Player 0.1.1 Beta'), StringStruct('FileVersion','0.1.1.0'), StringStruct('InternalName','RetroMindPlayer'), StringStruct('OriginalFilename','RetroMindPlayer.exe'), StringStruct('ProductName','RetroMind Player'), StringStruct('ProductVersion','0.1.1 Beta')])]), VarFileInfo([VarStruct('Translation',[1033,1200])])])'''
    (GENERATED/'version-info.txt').write_text(version_text,encoding='utf-8')
    print(f'Prepared original icon, version resources, and {len(urls)} upstream license/attribution files.')


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))
    main()
