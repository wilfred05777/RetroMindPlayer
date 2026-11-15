# Local Windows x64 build - 0.1.0 Beta

The source baseline uses PySide6/QML and Qt Multimedia's FFmpeg plugin for playback,
with a separate PyAV FFmpeg build for probing/artwork. The spec preserves both ABIs
and uses onedir (EXE + replaceable `_internal` runtime directory), never onefile.

Build requirements: Windows x64, Python 3.14 x64, the exact runtime/build packages
in build-requirements.txt, and Inno Setup 7.1.1 x64. These are build-host tools only;
end users do not install them. Download Inno Setup from https://jrsoftware.org/inno-setup/downloads
and verify its Authenticode signature before installation. The current official
7.1.1 compiler installer is signed by Pyrsys B.V. No security policy bypass is used.

```powershell
Set-Location 'C:\Users\wilfr\Desktop\RetroMindPlayer'
.\.venv\Scripts\python.exe -m pip install -r .\packaging\build-requirements.txt
.\packaging\build.ps1 -IsccPath '.\tools\InnoSetup7\ISCC.exe'
```

The build script runs tests by default, generates an original multiresolution ICO,
collects licence texts/attributions (cached under packaging/licenses), freezes the
application, audits the allowlisted bundle, builds setup, and writes a checksum.
`-SkipTests` is for an already-tested unchanged source build. `-InstallBuildDependencies`
explicitly installs the pinned build requirements. No publishing step exists.

Outputs:
- dist/0.1.0-beta/RetroMindPlayer/RetroMindPlayer.exe (keep the whole folder together)
- release/RetroMindPlayer-0.1.0-Beta-win64-Setup.exe
- release/RetroMindPlayer-0.1.0-Beta-win64-Setup.exe.sha256
- release/bundle-manifest.json and release notes/checklist/notices

Setup metadata: publisher Wilfred Bancairen, stable AppId
`{5C759A24-7B4C-4EE4-AB17-1E46217E6227}`. Keep it unchanged for future upgrades.
Install scope is current user, with Start menu and opt-in desktop shortcuts.
The installer first requests orderly shutdown over a per-user local IPC channel,
then uses Restart Manager file checks. Forced process termination is not configured. Normal user data remains under the same Qt organization/application
path, outside installation. Neither setup nor uninstall removes user data/media.

The entry point supplies the release version/icon and two explicit testing flags:
`--data-dir ABSOLUTE_PATH` overrides data only when explicitly supplied;
`--package-test ABSOLUTE_DIRECTORY` runs muted native diagnostics against generated
fixtures in that directory and writes a JSON report and screenshot there. Neither
flag is used by shortcuts or normal startup. The diagnostic is not an AI feature.

Official references checked 2026-11-15:
- https://pyinstaller.org/en/stable/index.html
- https://pyinstaller.org/en/stable/spec-files.html
- https://pyinstaller.org/en/stable/CHANGES.html (Python 3.14 support from 6.15)
- https://jrsoftware.org/inno-setup/downloads (current 7.1.1)
- https://jrsoftware.org/inno-setup/documentation/topic_setup_privilegesrequired.htm
- https://jrsoftware.org/inno-setup/documentation/topic_setup_appid.htm
- https://jrsoftware.org/inno-setup/documentation/topic_setup_closeapplications.htm
- https://jrsoftware.org/inno-setup/documentation/topic_archidentifiers.htm
- https://doc.qt.io/qt-6/windows-deployment.html
- https://doc.qt.io/qt-6/qtmultimedia-attribution-ffmpeg.html

Qt's older PyInstaller guide still contains a March 2021 Qt 6 caveat; the current
PyInstaller Qt hooks and actual frozen-runtime checks are used instead of treating
that historical paragraph as current compatibility evidence. See verification
results for the actual produced binaries. The installer and app are unsigned.

The included GPL/LGPL components require redistribution preparation; notices do
not relicense RetroMind's source. This task builds and tests locally only. See
THIRD_PARTY_NOTICES.md before any public or third-party release.

On a host that blocks .ps1 execution, leave its security policy unchanged and use
the same build driver directly:

```powershell
.\.venv\Scripts\python.exe .\packaging\build_release.py
.\.venv\Scripts\python.exe .\packaging\verify_release.py --install
```

The lifecycle verifier refuses an already-existing installation to avoid replacing
one it did not create. It creates and removes only this beta's test installation;
generated test data/reports remain in build/release-verification for inspection.
It uses a private per-process environment namespace for IPC to avoid interfering
with another app instance. Windows execution policy was not changed for this build.
