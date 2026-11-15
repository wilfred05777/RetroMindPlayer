# RetroMind Player 0.1.0 Beta - local packaging verification

Date: 2026-11-15 (Asia/Manila). Publisher: Wilfred Bancairen.
Target: Windows x64. Tested host: Windows 11 build 26200 x64.
Setup and application PE machine: AMD64 / 0x8664. Both are unsigned.

## Deliverable

- Setup: release/RetroMindPlayer-0.1.0-Beta-win64-Setup.exe
- Size: 71,560,449 bytes
- SHA-256: `0068fffd50d23e437f63439f43d039001200885f9137b5e1675b166b4322d07f` (recomputed and matched the .sha256 file)
- Bundle: 2084 files, 267,086,305 bytes,
  PyInstaller onedir with replaceable _internal runtime files.
- Stable AppId: {5C759A24-7B4C-4EE4-AB17-1E46217E6227}.
- Normal install: %LOCALAPPDATA%\Programs\RetroMindPlayer.
- Normal user data: %LOCALAPPDATA%\RetroMind\RetroMindPlayer (unchanged identity).

## Build and source checks

- Python 3.14.7 x64, PyInstaller 6.22.3, hooks-contrib 2026.10,
  PySide6 6.12.0, Mutagen 1.48.1, PyAV 18.1.0, Inno Setup 7.1.1 x64.
- Source tests after packaging/IPC changes: **31 passed, 1 xfailed in 16.73s**.
- Separate graceful installer-shutdown regression: **1 passed in 1.57s**.
- Python compilation and pip dependency check passed; git diff check passed.
- Inno compiler download and compiler Authenticode signatures were valid,
  signed by Pyrsys B.V. This does not sign the produced RetroMind installer.
- PowerShell execution policy blocked running .ps1 files; it was not changed.
  The supplied PowerShell wrapper was not executed. The same Python build driver
  was executed successfully, and invokes the actual PyInstaller and ISCC tools.

## Automated frozen-runtime verification

Copied the entire onedir build into a temporary directory outside the source tree.
Launched it there with PYTHONPATH/PYTHONHOME/virtual-environment/Qt developer plugin
paths removed and PATH restricted to Windows system directories. Its own JSON
report confirms `frozen: true` and the external executable path.

Both the external copy and installed executable passed:

- QML load without runtime warnings; application icon decoding; silent startup.
- Background recursive discovery, import preview/confirmation, duplicate import.
- MP4 metadata-failure fallback retained the file with a warning.
- Background thumbnail generation/cache and visible artwork/fallbacks.
- WAV decoded audio, H.264/AAC MP4 decoded picture/audio, VP9/Opus WebM picture/audio.
- Pause, seek and volume bindings on the one Qt media player/audio output.
- Video fullscreen enter/exit without source/position reset, audio/video/audio
  transition and clearing of stale video frames.
- Playlist, favourite, history and setting persistence in isolated test data.

The existing source playback backend is unchanged: Qt Multimedia FFmpeg 9.0.1 for
playback, with separate PyAV FFmpeg libraries for metadata/artwork. No VLC or
external ffmpeg executable is required. Original packaging generated fixtures,
logs and temporary databases are not part of the release bundle.

## Automated installation lifecycle

- Silent per-user install completed with no administrative install mode or reboot.
  Installer log confirms 64-bit Setup and HKCU registration.
- Version/publisher metadata, Start menu shortcut and opt-in desktop shortcut passed.
- Installed executable passed the same frozen media/QML tests.
- Same-version upgrade with the installed app open completed successfully. Stable
  AppId reused the installation; app-specific per-user IPC closed the player
  gracefully and allowed saving state/draining workers. No force-kill configured.
- Library tracks, playlist membership/order, favourites, history and non-layout
  settings matched across the upgrade. Window geometry is allowed to save on close.
- Installed app launched after upgrade.
- Uninstall removed application binary, shortcuts and uninstall entry. Test data
  and media outside installation were preserved byte-for-byte.
- Existing actual RetroMind user data matched its before/after hashes during the
  final lifecycle run. The first diagnostic attempt generated only Qt QML cache
  files in the default cache location; later runs redirect that cache too. The
  existing library database and original media were never imported into the build.
- The test installation was uninstalled after verification. Run setup to install
  for normal use; generated QA data remains under build/release-verification.

An earlier upgrade attempt exposed Restart Manager being blocked by an elevated
McAfee service that also had a file open. This was resolved through graceful
app-specific IPC before file replacement, without modifying security software or
settings. The final repeated lifecycle test passed. QML/plugin and multimedia
checks exposed no new packaging dependency/playback failures.

## Visual/manual evidence and limits

The installed UI screenshot was visually inspected: real generated media rows,
video thumbnails, fallback artwork, vector controls and layout rendered correctly.
No interactive installer-wizard navigation or native file-picker clicks were
performed during packaging verification; installation was automated/silent and
preview used the same application/controller flow.

The owner manually confirmed audible sound, seeking, fullscreen and switching
tracks in the Git-saved source baseline. Packaged automated playback was muted;
physical speaker output, subjective long-form sync and smooth 4K were not verified.
The known AV1 no-picture limitation remains the one expected test failure; successful
MP4 import is not a claim that every codec/profile decodes. HEVC/MKV were checked
in the source suite, not separately in this packaged diagnostic.

**No clean-machine/VM test was performed.** No Windows 10 or Arm64 test was performed.
The bundled interpreter and dependencies are present and developer paths were
removed for the frozen checks, but the host still has development software.
Use CLEAN_MACHINE_CHECKLIST.md on a fresh standard-user Windows PC.

No build was published/uploaded. This is an unsigned local evaluation beta.
THIRD_PARTY_NOTICES.md and 79 upstream licence/attribution files are included.
Public/third-party redistribution still requires a compatible RetroMind application
licence and complete matching copyleft source/source-offer preparation; the local
packaging work does not select an application licence or complete that release step.

Detailed local reports and installer logs: build/release-verification/.
Build recipe and checked official references: packaging/README.md.
