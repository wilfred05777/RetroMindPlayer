"""Exercise copied frozen runtime and optional per-user installer lifecycle locally."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import winreg
import uuid

ROOT=Path(__file__).resolve().parents[1]
KEY=r'Software\Microsoft\Windows\CurrentVersion\Uninstall\{5C759A24-7B4C-4EE4-AB17-1E46217E6227}_is1'


def snapshot(directory):
    return {str(p.relative_to(directory)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file()} if directory.exists() else {}


def library_state(directory):
    with sqlite3.connect(directory/'library.sqlite3') as db:
        result={table:db.execute(f'SELECT * FROM {table} ORDER BY 1,2').fetchall()
                for table in ('tracks','playlists','playlist_tracks','history')}
        result['settings']=[row for row in db.execute('SELECT * FROM settings ORDER BY key')
                            if row[0] not in ('window_width','window_height','sidebar_width','right_width')]
        return result


def installed_entry():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,KEY) as key:
            return {name:winreg.QueryValueEx(key,name)[0] for name in ('DisplayName','DisplayVersion','Publisher','InstallLocation')}
    except FileNotFoundError:
        return None


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--install',action='store_true',help='Install, same-version upgrade and uninstall this local beta')
    args=parser.parse_args()
    qa=ROOT/'build/release-verification'; qa.mkdir(parents=True,exist_ok=True)
    # Do not accidentally uninstall a user's previous installation.
    installed=Path(os.environ['LOCALAPPDATA'])/'Programs/RetroMindPlayer'
    if args.install and (installed_entry() or installed.exists()):
        raise RuntimeError('An installation already exists; refusing automated lifecycle changes to it')
    source_data=Path(os.environ['LOCALAPPDATA'])/'RetroMind/RetroMindPlayer'
    original=snapshot(source_data)
    clean=os.environ.copy()
    for key in ('PYTHONPATH','PYTHONHOME','VIRTUAL_ENV','QT_PLUGIN_PATH','QML2_IMPORT_PATH','QML_IMPORT_PATH','PYSIDE_DESIGNER_PLUGINS'):
        clean.pop(key,None)
    clean['RETROMIND_TEST_INSTANCE_NAMESPACE']=uuid.uuid4().hex
    clean['QML_DISK_CACHE_PATH']=str(qa/'qml-cache')
    clean['PATH']=str(Path(os.environ['WINDIR'])/'System32')+os.pathsep+os.environ['WINDIR']
    results={'checks':[], 'failures':[], 'clean_machine':False, 'signed':False}
    portable=Path(tempfile.mkdtemp(prefix='RetroMind-Beta-QA-')).resolve()
    assert portable.parent == Path(tempfile.gettempdir()).resolve() and portable.name.startswith('RetroMind-Beta-QA-')
    # Keep artifacts for inspection; no recursive cleanup of user paths.
    results['external_portable_copy']=str(portable)
    def call(command, **options):
        process=subprocess.run([str(arg) for arg in command],cwd=portable,env=clean,timeout=240,**options)
        if process.returncode:
            raise RuntimeError(f'Exit {process.returncode}: {command[0]}')
    try:
        bundle=ROOT/'dist/0.1.0-beta/RetroMindPlayer'
        shutil.copytree(bundle,portable/'app')
        subprocess.run([sys.executable,str(ROOT/'packaging/make_test_media.py'),str(qa/'portable')],cwd=ROOT,check=True)
        call([portable/'app/RetroMindPlayer.exe','--package-test',qa/'portable'])
        report=json.loads((qa/'portable/package-test-report.json').read_text())
        assert report['success'] and report['frozen'],report
        results['portable']=report
        results['checks'].append('Copied onedir runtime passes frozen QML/media/fullscreen/import/artwork diagnostics with developer paths removed')
        if args.install:
            setup=ROOT/'release/RetroMindPlayer-0.1.0-Beta-win64-Setup.exe'
            call([setup,'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/CURRENTUSER','/TASKS=desktopicon',f'/LOG={qa / "install.log"}'])
            entry=installed_entry()
            assert entry and entry['Publisher']=='Wilfred Bancairen',entry
            assert (installed/'RetroMindPlayer.exe').is_file()
            start=Path(os.environ['APPDATA'])/'Microsoft/Windows/Start Menu/Programs/RetroMind Player/RetroMind Player.lnk'
            # User desktop can be redirected to OneDrive; ask the shell for its actual location.
            import ctypes
            buffer=ctypes.create_unicode_buffer(32768)
            assert ctypes.windll.shell32.SHGetFolderPathW(None,0x10,None,0,buffer)==0
            desktop=Path(buffer.value)/'RetroMind Player.lnk'
            assert start.exists() and desktop.exists()
            results['checks'].append('Per-user install, publisher/version registry metadata, Start menu and optional desktop shortcut')
            subprocess.run([sys.executable,str(ROOT/'packaging/make_test_media.py'),str(qa/'installed')],cwd=ROOT,check=True)
            call([installed/'RetroMindPlayer.exe','--package-test',qa/'installed'])
            report=json.loads((qa/'installed/package-test-report.json').read_text())
            assert report['success'] and report['frozen'],report
            results['installed']=report
            test_data=qa/'installed/userdata'
            before_upgrade=library_state(test_data)
            before_media=snapshot(qa/'installed/fixtures')
            # Launch silently with a separate folder; Restart Manager should close it on upgrade.
            running=subprocess.Popen([str(installed/'RetroMindPlayer.exe'),'--data-dir',str(test_data)],cwd=portable,env=clean)
            time.sleep(2)
            assert running.poll() is None
            call([setup,'/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/CURRENTUSER','/CLOSEAPPLICATIONS','/NORESTARTAPPLICATIONS',f'/LOG={qa / "upgrade.log"}'])
            running.wait(timeout=20)
            assert running.returncode==0, 'App did not shut down cleanly during upgrade'
            assert library_state(test_data)==before_upgrade, 'Library changed during upgrade'
            assert installed_entry()['InstallLocation']==entry['InstallLocation']
            results['checks'].append('Same-version upgrade uses stable AppId, closes running app cleanly, and preserves library records/settings/history/playlists/favourites')
            call([installed/'RetroMindPlayer.exe','--smoke-test','--data-dir',qa/'installed/userdata'])
            results['checks'].append('Installed app launches after same-version upgrade')
            before_uninstall=snapshot(test_data)
            call([installed/'unins000.exe','/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',f'/LOG={qa / "uninstall.log"}'])
            for _ in range(100):
                if not (installed/'RetroMindPlayer.exe').exists() and not installed_entry():
                    break
                time.sleep(.1)
            assert not (installed/'RetroMindPlayer.exe').exists() and installed_entry() is None
            assert not start.exists() and not desktop.exists()
            assert snapshot(test_data)==before_uninstall
            assert snapshot(qa/'installed/fixtures')==before_media
            results['checks'].append('Uninstall removes binaries/shortcuts/entry and preserves external test user data and media')
        assert snapshot(source_data)==original, 'Existing actual user-data bytes changed'
        results['checks'].append('Existing actual RetroMind user data unchanged byte-for-byte; Qt test disk cache redirected')
        results['success']=True
    except Exception as error:
        results['success']=False
        results['failures'].append(str(error))
    finally:
        (qa/'verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        print(json.dumps({'success':results['success'],'checks':results['checks'],'failures':results['failures'],'report':str(qa/'verification.json')},indent=2))
    return 0 if results['success'] else 1


if __name__=='__main__':
    raise SystemExit(main())
