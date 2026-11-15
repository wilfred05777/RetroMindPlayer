# RetroMind Player 0.1.1 Beta - management menus and patch verification

Date: 2026-11-15, Asia/Manila. Publisher: Wilfred Bancairen.
Setup/application are Windows x64 and unsigned. Local build only; no publication.

## Delivered

- Setup: release/RetroMindPlayer-0.1.1-Beta-win64-Setup.exe
- Setup size: 71,583,014 bytes.
- SHA-256: `fb5ba998754d744edf0063373da27a22885826a51c673c92f91583d55cef73aa`; recomputed and matched the adjacent checksum file.
- Onedir: dist/0.1.1-beta/RetroMindPlayer/RetroMindPlayer.exe.
- Stable AppId retained: {5C759A24-7B4C-4EE4-AB17-1E46217E6227}.
- Existing 0.1.0 setup/checksum retained for the real upgrade test.
- Bundle audited: 2088 files; no personal database, media,
  logs, tests, virtual environment or secrets included by the data allowlist.

## Implementation

User playlists have sidebar hover/focus ellipsis and right-click menus, plus a
heading menu. Play targets the named playlist independently of the current view;
empty playlists cannot play. Rename is prefilled, rejects blank/duplicate names,
saves immediately and persists. Delete confirms the name and explains that media
and library records remain. Built-in views have no delete menu and are rejected
by repository/controller guards. Deleting the viewed playlist opens All media.

Rows, grid cards and Home cards share explicit-target menus: Play, queue,
playlist submenu, favourites, contextual membership removal, confirmed library
removal, File Explorer and Details. Missing-file/queue-only contexts hide unavailable
actions without blank slots. Menus stay within window bounds, have keyboard focus,
and support arrows, Enter, Escape, menu key and Shift+F10. Opening by right click,
ellipsis or focused-button keyboard activation does not start playback. Global
Space yields to focused controls and menus. Stale selected-row controls clear.

Playlist membership is already unique per playlist/track pair; repeated entries
are not supported, so no membership-ID migration is needed. Membership removal
keeps remaining relative order, library/favourites, other playlists and playback.
Playlist deletion and library removal use transactions, explicit reference cleanup,
and rollback on errors. Library removal cleans memberships/history/bookmarks and
never deletes or moves source files. Re-import may re-add the source.

The in-memory queue stays independent of playlist storage. Deleting a library item
prunes all queue references; deleting the current item stops/clears Now Playing,
video frames and fullscreen. A cursor gap keeps next/previous navigation correct,
and stale end-of-media notifications cannot restart a removed source. Existing
playback engine, import logic and schema version 2 remain unchanged.

## Actual automated source checks

- Final full suite: **43 passed, 1 xfailed in 22.76 seconds**.
- Dedicated management suite after final selection update: **12 passed**.
- Final 200% Qt scale-factor management suite: **12 passed in 7.59 seconds**.
- Earlier 150% management suite: **10 passed in 6.53 seconds**, before the two
  additional video-removal/missing-context cases were added.
- Playback missing/corrupt automatic-advance case repeated in five fresh isolated
  processes/directories: **five passed**.
- Compilation, dependency check and diff whitespace checks passed. Git reports
  a line-ending normalization notice for release notes, not a whitespace failure.

Tests exercise rename/delete persistence, blank/duplicate rejection, protected
views, SQL rollback after reference cleanup, reference integrity, original-file
hash preservation and re-import. They verify removal from one playlist keeps other
playlists/favourites/order, queue continuity, current audio/video removal including
fullscreen/frame clearing, stale end events, and valid navigation after pruning.
Native QML tests send real pointer/keyboard events for clicked-target row/card
menus, submenu selection, favourites, queueing, Details, ellipsis buttons,
confirmation cancellation/acceptance and empty/missing contexts. No QML runtime
warnings were observed in successful interaction tests. Scaled tests scroll cached
virtualized delegates into view and click their visible portion; cached items may
otherwise be clipped in a small viewport. Scaling uses QT_SCALE_FACTOR, not a
change to Windows display settings.

## Frozen application and actual 0.1.0 to 0.1.1 upgrade

Executed packaging/verify_release.py --install --upgrade-from the retained 0.1.0
setup against the final rebuilt installer. Its JSON report confirms success:

- External temporary copy of the frozen onedir app launches with developer paths
  removed. QML/icon/artwork/import/duplicates, WAV decoded audio, H.264/AAC MP4 and
  VP9/Opus WebM decoded picture/audio, seek/volume and fullscreen checks pass.
- Frozen management menus open without warnings; explicit media target, persisted
  rename, membership removal, cancelled/confirmed removals, built-in protection,
  queue pruning and original-file retention checks pass.
- Per-user 0.1.0 installation, publisher metadata, Start menu and optional desktop
  shortcut succeed. Generated media/test database are outside installation.
- Upgrade to 0.1.1 with the 0.1.0 app open closes it gracefully, reuses the same
  AppId/path, reports DisplayVersion 0.1.1 and preserves tracks, memberships/order,
  favourites, history and non-layout settings. Normal window layout may save on
  close; application identity and data directory are unchanged.
- The upgraded frozen 0.1.1 app passes the media/management diagnostic and relaunch.
- Uninstall removes app/shortcuts/uninstall entry and keeps test data/media.
- Existing actual RetroMind user data matches before/after hashes. The test
  installation was removed after verification; normal use requires running setup.
- Installed-menu screenshots were visually inspected. The frozen diagnostic opens
  menus programmatically; source QML tests cover actual right-click/ellipsis events.

The final onedir Python archive was produced by PyInstaller after passing the full
suite. Its final external QML selection-state asset was then refreshed from the
verified source, the bundle re-audited, and Inno Setup recompiled. Source/bundled
Main.qml bytes and final setup checksum were explicitly compared. The normal full
build script collects the same complete QML assets on a new build.

Local detailed reports/logs: build/release-verification-0.1.1/verification.json and
portable/installed package-test-report.json, plus install/upgrade/uninstall logs.

## Manual/API checks, limitations and anomalous run

The File Explorer shell API returned success for a generated path containing an
apostrophe and Unicode; the file bytes were unchanged. Its visual selection was
not manually inspected. The installed dark menu screenshot was visually reviewed.
The owner previously confirmed sound/seeking/fullscreen/track switching in the
source baseline. Packaged checks were muted; audible packaged speaker output,
long-form synchronization, live monitor/DPI transitions and smooth 4K remain
manual checks. No clean-machine/VM test, Windows 10 or Arm64 test was performed.
The known AV1 no-picture limitation remains the one expected test failure.

One initial full run encountered `database disk image is malformed` in the shared
Windows TEMP database for the existing automatic-advance test. Inspection of a
copy confirmed that temporary database was malformed. No causal fix is claimed;
the cause was not established. It did not recur in subsequent complete suites
using unique workspace-local temporary directories, five isolated repetitions,
or frozen/install/upgrade checks. The failing temporary copy is under
build/qa-temporary-db-investigation; no actual user library was involved. This
anomaly remains recorded rather than being treated as proof of a resolved cause.

The installer is unsigned and nothing was uploaded. Public/third-party distribution
still requires the licensing/corresponding-source preparation described in
THIRD_PARTY_NOTICES.md. The prior 0.1.0 report is retained as VERIFICATION-0.1.0.md.

## Launch from the project directory

```powershell
.\.venv\Scripts\python.exe -m retromind.main
```

Or launch the bundled app without Python:

```powershell
.\dist\0.1.1-beta\RetroMindPlayer\RetroMindPlayer.exe
```
