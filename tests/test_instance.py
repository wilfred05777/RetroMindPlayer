"""The installer shutdown request must preserve data and exit gracefully."""
from pathlib import Path
import os
import sqlite3
import subprocess
import sys
import time
import uuid


def test_graceful_installer_shutdown_in_separate_process(tmp_path):
    environment=os.environ.copy()
    environment['RETROMIND_TEST_INSTANCE_NAMESPACE']=uuid.uuid4().hex
    environment['QML_DISK_CACHE_PATH']=str(tmp_path/'qml-cache')
    command=[sys.executable,'-m','retromind.main']
    process=subprocess.Popen(command+['--data-dir',str(tmp_path/'data')],env=environment)
    try:
        end=time.monotonic()+15
        database=tmp_path/'data/library.sqlite3'
        while time.monotonic()<end and not database.exists():
            assert process.poll() is None
            time.sleep(.05)
        assert database.exists()
        time.sleep(.5)
        client=subprocess.run(command+['--quit-for-update'],env=environment,timeout=35)
        assert client.returncode==0
        assert process.wait(timeout=10)==0
        with sqlite3.connect(database) as db:
            assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            assert db.execute("SELECT count(*) FROM settings WHERE key='window_width'").fetchone()[0]==1
    finally:
        if process.poll() is None:
            subprocess.run(command+['--quit-for-update'],env=environment,timeout=35)
            process.wait(timeout=10)
