# Clean-machine checklist - 0.1.1 Beta x64

Use a fresh Windows 10 (build 19041+) / Windows 11 x64 VM or PC, standard account,
with no Python, Qt, VS Code, FFmpeg, developer tools or project folders installed.
This checklist is not marked complete by tests on the development machine.

- [ ] Verify the supplied SHA-256 checksum and the expected unsigned status.
- [ ] Run setup normally without administrator access; inspect version/publisher.
- [ ] Confirm Start menu shortcut and optional desktop shortcut.
- [ ] Launch from shortcut and installation directory with no source/dev PATH.
- [ ] Confirm QML layout, vector icons and gradients; no missing-plugin messages.
- [ ] Import real mixed media using Open files, folder selection/recursive preview,
      drag/drop, Unicode/apostrophe paths and .MP4 filenames. Inspect counts/reasons.
- [ ] Confirm thumbnails and missing-art fallback; unsupported metadata still imports.
- [ ] Play H.264/AAC MP4 and WAV: actual picture, speaker sound and long-form sync.
- [ ] Check play/pause, stop, seek, volume/mute, next/previous, shuffle/repeat.
- [ ] Check fullscreen button, double-click, Escape and audio/video/audio changes.
- [ ] Check WebM VP9/Opus, MKV and HEVC with representative real files; record exact
      codecs/profiles/results. AV1 is a known limitation, not a guaranteed format.
- [ ] Test 100/125/150/200% display settings, monitor changes and resizing.
- [ ] Create mixed playlists, reorder, favourite, play tracks and save settings.
- [ ] Close/relaunch: verify all data and silent startup.
- [ ] Run next-version installer with app open; accept close-app prompt; confirm
      orderly shutdown, single installation/uninstall entry and preserved data.
- [ ] Uninstall: binaries/shortcuts removed; AppData library and original media remain.
- [ ] Reinstall and confirm retained data returns.
- [ ] Record OS build, hardware, display scaling, sample codecs, errors and logs.

Do not disable SmartScreen, Defender, UAC or driver-signing protections. If policy
blocks an unsigned beta, use normal organizational approval or a signed release.
