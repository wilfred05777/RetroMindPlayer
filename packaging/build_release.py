"""Local Windows build driver; also used by the PowerShell wrapper."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import shutil
import struct
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--iscc',type=Path,default=ROOT/'tools/InnoSetup7/ISCC.exe')
    parser.add_argument('--skip-tests',action='store_true')
    parser.add_argument('--install-build-dependencies',action='store_true')
    args=parser.parse_args()
    assert sys.platform=='win32' and struct.calcsize('P')==8, 'Windows x64 Python required'
    assert sys.version_info[:2]==(3,14), 'This pinned beta build uses Python 3.14 x64'
    iscc=args.iscc.resolve()
    assert iscc.is_file(), 'Supply a verified Inno Setup 7.1.1 ISCC.exe'
    def call(*command):
        subprocess.run([str(value) for value in command],cwd=ROOT,check=True)
    if args.install_build_dependencies:
        call(sys.executable,'-m','pip','install','-r','packaging/build-requirements.txt')
    assert importlib.metadata.version('pyinstaller')=='6.22.3'
    call(sys.executable,'-m','pip','check')
    if not args.skip_tests:
        test_temp=ROOT/'build'/('qa-build-tests-'+uuid.uuid4().hex)
        assert not test_temp.exists()
        call(sys.executable,'-m','pytest','-q','--basetemp',test_temp)
    release=ROOT/'release'; release.mkdir(exist_ok=True)
    shutil.copy2(iscc.parent/'license.txt',ROOT/'packaging/licenses/Inno-Setup-LICENSE.txt')
    call(sys.executable,'packaging/prepare_release.py')
    dist=ROOT/'dist/0.1.1-beta'
    call(sys.executable,'-m','PyInstaller','--noconfirm','--clean','--distpath',dist,
         '--workpath',ROOT/'build/pyinstaller','packaging/RetroMindPlayer.spec')
    bundle=dist/'RetroMindPlayer'
    call(sys.executable,'packaging/audit_bundle.py',bundle,release/'bundle-manifest.json')
    call(iscc,f'/DBundleDir={bundle}',f'/DReleaseDir={release}','packaging/RetroMindPlayer.iss')
    setup=release/'RetroMindPlayer-0.1.1-Beta-win64-Setup.exe'
    digest=hashlib.sha256(setup.read_bytes()).hexdigest()
    setup.with_suffix('.exe.sha256').write_text(f'{digest}  {setup.name}\n',encoding='ascii')
    for filename in ('RELEASE_NOTES.md','CLEAN_MACHINE_CHECKLIST.md','THIRD_PARTY_NOTICES.md'):
        shutil.copy2(ROOT/'packaging'/filename,release/filename)
    print(f'Built local unsigned installer: {setup}',flush=True)
    print(f'SHA256 {digest}',flush=True)


if __name__=='__main__':
    main()
