# RetroMind Player 0.1.1 Beta

Publisher: Wilfred Bancairen. Windows x64 local beta; unsigned.

## Changes from 0.1.0 Beta

- User playlists have hover/focus ellipsis buttons, right-click menus and a menu
  beside the opened heading: Play, Rename and confirmed Delete.
- Media rows and cards share Play, Add to queue, Add to playlist submenu,
  favourites, contextual Remove from this playlist, confirmed Remove from library,
  Show in File Explorer and Details. Keyboard menu key/Shift+F10, Enter and Escape
  are supported. Actions target the clicked item; opening a menu does not play it.
- Rename is prefilled, rejects blank/duplicate names, saves immediately and
  persists. Cancelled delete/removal confirmations leave records unchanged.
- Playlist entry removal/deletion preserves the library, source files, other
  playlists and the independent active playback queue.
- Removing a library item cleans playlist/history/bookmark references in one
  transaction. Removing the current item stops and clears Now Playing, prunes the
  queue, and keeps next/previous navigation valid. Source files are never deleted
  or moved. Re-importing the source folder can restore a removed library entry.
- Existing playlists contain each track at most once; entries use the existing
  playlist/track key. Relative order is preserved. No schema migration is needed.

## Installation and data

Python, Qt/QML, Qt Multimedia FFmpeg and PyAV probing/artwork libraries are bundled.
Users do not install Python, VS Code or development tools. Per-user install goes
under %LOCALAPPDATA%\Programs\RetroMindPlayer, with Start menu and optional desktop
shortcuts. User data stays in %LOCALAPPDATA%\RetroMind\RetroMindPlayer. The stable
AppId is unchanged from 0.1.0. Setup/uninstall do not delete user data or media.
No personal database, logs or media are bundled. Startup remains silent.

## Playback limitations and verification

Playback remains Qt Multimedia's bundled FFmpeg backend, not VLC. Existing
software rendering/decoding defaults and environment overrides remain. MP4 is a
container, not a decoder guarantee. AV1 no-picture is a known limitation of this
Qt build, separate from successful import/probing. No codec pack or transcoder is
installed. Smooth 4K and every codec/profile/hardware combination are not promised.

The owner manually confirmed sound, seeking, fullscreen and track switching in
the source baseline. Automated frozen checks use muted generated fixtures and do
not establish physical speaker sound or long-form synchronization on a clean PC.
See VERIFICATION.md for actual tests and CLEAN_MACHINE_CHECKLIST.md for pending
manual checks. Clean-machine testing has not been performed.

No upload/publication. This unsigned installer is for local evaluation. Public or
third-party redistribution requires compatible application licensing and matching
copyleft source/source-offer preparation; see THIRD_PARTY_NOTICES.md.
