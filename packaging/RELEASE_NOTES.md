# RetroMind Player 0.1.0 Beta

Publisher: Wilfred Bancairen. Windows x64 local beta; unsigned.

Includes the existing dark QML interface, local audio/video library, recursive
import preview, mixed playlists, favourites/history, thumbnails, fullscreen and
refined transport controls. Python, Qt/QML, Qt Multimedia FFmpeg and PyAV probing
libraries are bundled; users do not install Python or developer tools.

Installation is per user under %LOCALAPPDATA%\Programs\RetroMindPlayer, with a
Start menu shortcut, optional desktop shortcut and an uninstaller. App data stays
in %LOCALAPPDATA%\RetroMind\RetroMindPlayer. Upgrades/uninstall do not delete
library databases, playlists, favourites, history, settings, cache or source media.
The installer includes no personal media, database or logs. Startup stays silent.

Playback is Qt Multimedia with its bundled FFmpeg backend, not VLC. Software
rendering/decoding defaults and explicit environment overrides are retained.
MP4 is a container, not a decoder guarantee. The installed Qt build has a known
AV1 no-picture limitation, independent of successful PyAV probing/import. Generated
H.264/AAC MP4/MKV, VP9/Opus WebM, HEVC/AAC MP4 and video-only H.264 were verified
in the source baseline. Smooth 4K, every codec/profile and all hardware are not
promised. No transcoding, codec-pack installation or security-setting changes.

The owner manually confirmed sound, seeking, fullscreen and track switching in
the source version. Packaged checks use muted generated fixtures; they do not
establish audible sound or long-form lip sync on a clean PC. See the release
verification report and clean-machine checklist for precisely executed checks.

This is a local evaluation build, not a public release. Clean-machine verification,
code signing and redistribution source/licensing requirements remain release
steps; see THIRD_PARTY_NOTICES.md. No publication or upload was performed.
