# MP4 discovery and import verification - 2026-11-15

This report supersedes the earlier folder-preview verification. Native Windows,
project-local `.venv`, PySide6 6.12.0, PyAV 18.1.0, pytest 9.2.0.

## Cause and scope

The native directory-only picker hides files by design; its empty file view is
not evidence of failed scanning. The existing scanner already lowercased file
extensions, and the accessible SQL course MP4 could be probed successfully.
However, the previous in-app preview listed only a single directory while import
scanned recursively. Import also treated a metadata-reader exception as fatal for
MP4. These were actual gaps in the full flow, independent of dialog filters.

## Implemented flow

1. Import folder opens the directory-only picker labelled exactly:
   `Select a folder; files will appear in the next preview.`
2. Accepted selection invokes background recursive discovery, without metadata,
   thumbnail, or codec decoding. Empty/nonlocal selections cannot scan the cwd.
3. The application previews the scanner's snapshot, including relative nested
   paths, unsupported-file reasons and directory traversal errors.
4. Import discovered files imports that exact list, checking access and canonical
   duplicate identity. Scan again refreshes the snapshot. All processing stays in
   workers; the library is untouched until import is requested.

Supported extensions are case-insensitive. Windows extended paths are used for
long-path I/O while canonical library keys keep the old format. Video metadata
exceptions retain the file with filename fallback and unknown stream fields,
plus an explicit warning. Thumbnail failures emit fallback artwork independently
of import. Missing/unreadable files and persistence errors remain failures.

The result reports discovered supported files, imported, skipped, failed,
metadata warnings and pending files after cancellation. Unsupported extensions and
duplicates are skipped with reasons. The separate Open files action includes
lower/uppercase media filters and All files. Playback and schema were not changed.

## Executed checks

- Final full suite: **27 passed, 1 xfailed in 31.59 seconds**.
- `python -m compileall -q retromind tests`: passed.
- `python -m retromind.main --smoke-test`: native startup/exit passed.
- `git diff --check`: passed.
- Native QML preview screenshot visually inspected: Unicode/apostrophe path,
  uppercase MP4 and a recursively discovered nested audio file are visible.

Tests cover the shared QML selection handler, exact selected-path forwarding,
background discovery, rendered preview binding, no insertion before confirmation,
import signal routing, Open files import/filters, and duplicate reasons. Native
picker interaction itself was not clicked manually: the same handler used by its
accepted signal was invoked with a real local QUrl.

Service tests create actual media under spaces, apostrophes, Unicode, and a Windows
path longer than 320 characters. They verify recursive discovery, `.MP4` matching,
long-path probe/import and canonical duplicate identity, metadata fallback with
unknown fields, thumbnail failure isolation, missing/unreadable file reasons,
unsupported extensions, scan permission errors and cancellation. Existing database
migration, playlists, history, settings and real audio/video playback tests pass.

## Actual selected folder

Inspected the accessible Downloads folder matching `SQL Full Course for Beginners
(30 Hours) ... From Zero to Hero`. Ran the Controller preview and import methods
with a separate temporary SQLite database, not the user's app library:

- Preview: **2 supported files discovered, 4 skipped, 0 failed directories**;
  six entries, and no library records before confirmation.
- Import: **2 imported, 4 skipped, 0 failed, 0 warnings, 0 pending**.
- Media: one AAC audio file and one 3840x2160 AV1/AAC MP4.
- Skips: two `.srt` files, one `.jpg`, and one `.txt`, all explicitly reported
  as unsupported extensions.
- Source files and existing user library were not modified.

## Limits and local verification

The existing AV1 playback test is the one expected failure: the installed Qt
backend fails to produce video frames and the diagnostic is verified. This is
separate from discovery/import. This 30-hour course's full playback, physical
sound, lip sync and 4K smoothness were not verified. Other generated codec tests
continue to pass; this work makes no new codec-support claim.

To verify manually, restart the app, choose Import > Import folder, select the
course directory, inspect the recursive preview/counts, then choose Import
discovered files. Inspect Details for warnings or skipped/failed reasons. Repeat
the import to confirm duplicate skips. Open files can select the MP4 directly.
Test actual AV1 playback separately from import success.

```powershell
Set-Location 'C:\Users\wilfr\Desktop\RetroMindPlayer'
.\.venv\Scripts\python.exe -m retromind.main
```

# Bottom playback controls verification - 2026-11-15

This update changes QML presentation and adds control-specific tests only. No
playback engine, codec, database, or import implementation was changed.

Changes:
- Shared MediaSlider: 4px rounded dark-grey track, solid white fill from the left
  edge to the handle, 12px solid handle, and 32px invisible interaction height.
  Fill and handle use the same slider position geometry. No gradients.
- Seek is disabled and grey when duration is zero/unknown, with an explanatory
  accessible name. Existing seek/volume onMoved commands and value bindings remain.
- Original Qt Quick vector paths replace bottom transport font symbols: play,
  pause, previous, next, stop, shuffle, repeat/repeat-one, mute/volume, fullscreen,
  queue, video and favourite. Existing non-transport IconButton text uses remain.
- Play/pause keeps a fixed 42px footprint, white circular surface and black icon.
  Hover uses light grey, pressed uses darker grey, and keyboard focus shows an
  external white ring. Tooltip and accessible name bind to actual playback state.
  Active shuffle/repeat use the same green icon colour.

Executed:
- Full suite: **30 passed, 1 xfailed in 15.14 seconds**. The expected failure is
  the pre-existing AV1 decoder limitation, unrelated to this styling change.
- Dedicated control suite at 150%: **3 passed in 2.68 seconds**.
- Dedicated control suite at 200%: **3 passed in 2.88 seconds**.
- Python compilation, native startup smoke test, and git diff whitespace check
  passed.

The control suite checks both sliders at 0%, 50% and 100%, sampling actual
rendered white/grey pixels and checking fill/handle geometry. It sends pointer
click/drag and keyboard events, checks normal/hover/pressed button surface pixels,
exercises play and pause with Tab focus, and asserts unchanged button geometry.
An isolated real WAV/Qt session verifies enabled/disabled seeking, actual pause,
seek and volume actions, backend-to-control bindings, active shuffle/repeat
colours, and control bounds at 800x600 and 1440x900 logical window sizes. QML
runtime warning assertions passed.

Inspected captured screenshots of slider endpoints/midpoint, play/pause states,
keyboard focus, pressed pause at 150%, and complete narrow player layouts at
100% and 200%. Controls remained inside the window without layout shifts.

Scaling runs use native Windows Qt windows with QT_SCALE_FACTOR=1, 1.5 and 2;
Windows display settings were not changed. Live monitor/DPI transitions and
physical touchscreen interaction were not tested. Audio tests were muted and
used a temporary database and generated WAV; existing user media/library were
not altered.


# Windows 0.1.0 Beta packaging - 2026-11-15

Built and locally verified an unsigned Windows x64 PyInstaller onedir + Inno Setup
installer. Source regression results: 31 passed, 1 known AV1 expected failure.
Copied/installed frozen QML, import, artwork, decoded audio/video, seek, volume,
fullscreen and persistence checks passed. Per-user install, shortcuts, graceful
same-version upgrade, relaunch and uninstall passed, retaining library/media.
No clean-machine verification was performed. Detailed results and limits are in
[packaging/VERIFICATION.md](packaging/VERIFICATION.md). Owner-confirmed audible
source playback is distinct from muted packaged automated checks.
