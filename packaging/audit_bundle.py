"""Fail the build if required runtime files are absent or private data is included."""
from pathlib import Path
import hashlib
import json
import sys
import pefile

root=Path(sys.argv[1]).resolve()
output=Path(sys.argv[2]).resolve()
exe=root/'RetroMindPlayer.exe'
assert pefile.PE(str(exe)).FILE_HEADER.Machine == 0x8664, 'Application must be x64'
files=[p for p in root.rglob('*') if p.is_file()]
for file in files:
    rel=file.relative_to(root)
    assert not set(rel.parts) & {'.venv','.git','tests','__pycache__','.pytest_cache'}, rel
    assert file.suffix.lower() not in {'.sqlite3','.sqlite','.db','.log','.mp4','.webm','.mkv','.wav','.pfx','.pem','.key'}, rel
    assert file.name.lower() not in {'.env','credentials.json','token.json'}, rel
required = ('python314.dll','qwindows.dll','ffmpegmediaplugin.dll','avcodec-63.dll','Main.qml','retromind.ico','Qt6Quick.dll','Qt6Multimedia.dll')
for name in required:
    assert any(p.name.lower()==name.lower() for p in files), f'Missing {name}'
assert any(p.name.startswith('avcodec-62-') for p in files), 'Missing independent PyAV FFmpeg DLLs'
assert any('QtQuick/Shapes' in p.relative_to(root).as_posix() for p in files), 'Missing vector icon QML plugin'
assert not any('WebEngine' in p.name for p in files), 'Unused browser engine unexpectedly included'
manifest = dict(file_count=len(files), total_bytes=sum(p.stat().st_size for p in files), files=[dict(path=p.relative_to(root).as_posix(), size=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(files)])
output.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(f'Bundle audited: {len(files)} files, {manifest["total_bytes"]/1024**2:.1f} MiB; required runtimes present; no personal database/media/logs.')
