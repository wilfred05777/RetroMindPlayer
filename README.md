# RetroMind Player

A standalone Windows local music and video player, built with Python, PySide6/QML, Qt Multimedia, SQLite, Mutagen, and PyAV. The dark desktop layout keeps RetroMind branding and uses original colour surfaces and system font symbols; no Spotify integration, account, downloaded brand artwork, recommendations, or advertisements are included.

## Launch (PowerShell)

```powershell
Set-Location "C:\Users\wilfr\Desktop\RetroMindPlayer"
.\.venv\Scripts\python.exe -m retromind.main
```

No environment activation or execution-policy change is needed. Python 3.12+ is required; this checkout uses Python 3.14.7.

## Fresh setup

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m retromind.main
```

Use another installed Python 3.12+ version to create `.venv` if needed. `pyproject.toml` contains compatible dependency ranges, and `requirements-lock.txt` records the exact installed versions, including test tools. Optional editable installation: `.\.venv\Scripts\python.exe -m pip install -e ".[test]"`.

## Library and playlists

- **Import > Open files** chooses multiple audio/video files with `.mp4`/`.MP4` filters and an **All files** fallback. **Import folder** opens a directory-only picker labelled **Select a folder; files will appear in the next preview.** Selecting a folder starts recursive discovery in a background worker. The application then shows every discovered supported file, including nested paths, plus skipped files and scan errors with reasons. Click **Import discovered files** to import that exact snapshot; **Scan again** refreshes it. A folder-only Windows picker hiding files says nothing about scanner success. Local file drops import into the same library. The application references files in place; it does not copy, modify, or transcode media.
- Discovery uses case-insensitive extensions and does not open codecs or generate thumbnails. Import reports **discovered supported files**, **imported**, **skipped**, **failed**, metadata warnings, and pending items after cancellation. Unsupported extensions and existing library entries count as skipped; unavailable/unreadable files and database errors count as failed. Directory traversal errors are also reported explicitly. **Details** contains full paths and reasons. A video metadata-probe failure imports filename-based metadata with unknown stream fields and a warning; it does not reject the MP4 or claim playback support. Thumbnail work is separate and failures use fallback artwork. Windows I/O uses extended paths for long names while stored canonical paths retain the existing format for duplicate compatibility.
- The sidebar opens All media, Favourites, Recently added, Recently played, and named playlists. Home contains real recent items, an explicitly clicked resume action, and saved playlist cards. Empty libraries show setup guidance.
- Search matches title, artist, and album. Library filters select All, Audio, or Video. Sorting supports title, artist, date added, and duration. List/grid views are virtualized; artwork is requested lazily for instantiated items.
- Click a row to select it; double-click or press Enter on a focused row to play. A row's play and heart buttons operate directly. Grid cards play on click and have a separate Select button.
- Create a playlist with **+** in the sidebar. Select a media item and a destination dropdown, then **Add selected**. Open a playlist to rename it, remove selected items, or move them up/down. Audio and video can share a playlist. Title/order sorting preserves manual playlist order; other sorts temporarily display that order differently. Reordering restores manual order.
- Imports run off the GUI thread. Discovery, metadata, and insertion progress are shown. Cancel finishes the current probe/file first. **Details** reports skipped files and playback errors; tracebacks and paths are written to the log. Duplicate prevention uses canonical, case-normalized paths plus a SQLite uniqueness constraint.

## Playback and video

The persistent player provides favourite, shuffle, previous, play/pause, stop, next, repeat, seek, mute, volume, queue, video visibility, and fullscreen controls. Buttons expose accessible names and tooltips. Space toggles playback outside text fields; Ctrl+O opens files and Ctrl+F focuses search.

A single Qt media player and a single audio output play both media types. One `VideoOutput` is reparented for fullscreen; switching views never creates a second player. Video uses aspect-fit letterboxing without cropping. Double-click the picture or click fullscreen to enter/exit; Escape exits. Playback controls remain below fullscreen video. Paused frames are resubmitted after surface transitions without reloading or seeking the source. Audio-only sources clear the old picture. Hide the video stage to give the library more room while playback continues.

Playback queues snapshot the visible order when a media item starts. Queue entries can be played or removed without changing saved playlists. Shuffle keeps the current item and rearranges queue order; disabling shuffle restores original order for the remaining items. Repeat cycles off/all/one; repeat-one applies to natural track endings, while Next still advances. Automatic advancement skips missing files and decoder failures, with bounded attempts to avoid endlessly retrying an unavailable queue. A directly selected failing item reports an error; Next continues.

Volume, mute, shuffle/repeat, last selected playlist/view, sidebar/right-panel state, list/grid state, normal window dimensions, and panel widths persist. The right panel collapses first on narrow windows; the sidebar then becomes an icon rail. At small widths, Queue opens a dialog. Volume, transport, and favourite remain available. Home resumes the last bookmarked item only after a click. Startup never automatically plays audio. Queues themselves are session-local.

## Formats, metadata and thumbnails

Accepted audio extensions: `.mp3 .wav .flac .ogg .m4a`.

Accepted video extensions: `.mp4 .m4v .mkv .webm .mov .avi .wmv .mpg .mpeg .ts .m2ts`.

An extension identifies a possible container, not its codecs or decode capability. PyAV probes stream headers off the GUI thread to refine audio/video classification, read available container tags, duration, dimensions, and codec names. Attached cover pictures do not turn audio into video. Mutagen supplies audio tags, including WAV ID3 tags. Missing titles fall back to the filename stem; missing metadata stays unknown. The legacy duration field uses zero as its internal unknown sentinel and the UI displays `--:--` until a duration is available.

Background workers extract embedded MP3/FLAC/MP4/OGG covers or decode only the first video picture. They scale images before caching them in the user-data directory. Cache keys include canonical source path, size, and modification timestamp, so later requests invalidate changed sources. Missing artwork uses an original gradient/music/video fallback. Indexing does not decode entire videos. Thumbnail work uses at most two workers; failed or absent art never prevents playback.

Qt Multimedia performs actual playback; PyAV's ability to probe a stream does not guarantee Qt can play it. Settings shows Qt's runtime codec capability hints, but playback results are authoritative. The default selects Qt's FFmpeg backend, prefers software RHI rendering on Windows (D3D WARP), and disables hardware video decoding. AMD acceleration is not required. Explicit environment overrides are respected. Do not force the legacy `QT_QUICK_BACKEND=software` adaptation for this video UI; use the default RHI configuration. Qt documents the [software RHI preference](https://doc.qt.io/qt-6/qtquick-visualcanvas-scenegraph-renderer.html) and [FFmpeg hardware-decoding configuration](https://doc.qt.io/qt-6/advanced-ffmpeg-configuration.html); the latter is a private Qt configuration interface and may change in future Qt versions.

Verified small generated clips on this Windows environment:

| Container | Video codec | Audio codec | Result |
| --- | --- | --- | --- |
| MP4 | H.264 | AAC | Picture and decoded audio buffers verified |
| WebM | VP9 | Opus | Picture and decoded audio buffers verified |
| MKV | H.264 | AAC | Picture and decoded audio buffers verified |
| MP4 | HEVC/H.265 | AAC | Picture and decoded audio buffers verified |
| MP4 | H.264 | No audio stream | Picture verified |
| MKV | AV1 | Opus | Import works; this Qt build produces no picture; diagnostic verified |

AV1 is a known backend limitation here, not a guaranteed supported codec. A stream that reaches its end without any video frames gets a useful codec error instead of silently appearing to work. No codec pack or transcoder is installed automatically. Physical sound output, subjective lip sync, other profiles/bit depths, long files, and smooth 4K playback are not guaranteed; use the checklist below.

## Storage and migration

`QStandardPaths.AppLocalDataLocation` selects the same per-user directory as Phase 1, normally `%LOCALAPPDATA%\RetroMind\RetroMindPlayer`. It holds `library.sqlite3`, rotating `retromind.log` files, and a `thumbnails` cache directory.

The version 1 -> 2 migration adds columns and an index inside a transaction. Existing media IDs/paths, tags, favourites, playlists and positions, history, and settings are retained. Historical import dates and stream metadata that Phase 1 did not record remain unknown; new imports have their actual import timestamp. Original Phase 1 entries remain audio. Future schema versions are rejected. SQL values are parameterized and each repository operation closes its connection. Queue reads are batched and cached so position updates never query every queued file. Home queries request only eight recent items.

Exit cancels and joins importing, drains/cancels thumbnail work, stops bookmark timers, prevents pending callbacks from restarting playback, and detaches/releases the media source and video sink before QML destruction. Import cancellation/exit can wait for the current local metadata probe to return.

## Architecture and future extension point

- `qml/`: presentation, reusable controls/artwork/cards, responsive layouts and one video surface.
- `controller.py`: Qt commands/properties and coordination of the existing service boundaries.
- `services.py`: GUI-independent mixed-media importing and metadata reading.
- `repository.py`: additive schema migration and parameterized persistence.
- `queue_service.py`: GUI-independent queue, shuffle, repeat, and ordering rules.
- `playback.py`: one Qt player/audio output; the controller attaches the QML video sink.
- `artwork.py`: bounded workers and source-versioned image cache.
- `main.py`: app setup, same per-user paths, logging and lifecycle.

Future semantic retrieval or assistant tools can call the import, repository, queue, and playback command boundaries. They should not depend on QML. No assistant backend, embeddings, model integration, or non-functional chat UI is included.

## Automated checks

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m compileall -q retromind tests
.\.venv\Scripts\python.exe -m retromind.main --smoke-test
```

Tests open native Qt windows and require a Windows desktop and working Qt backend. Generated clips and SQLite databases are isolated in pytest's temporary directories. Audio volume is zero; decoded audio buffers are checked without making sound. The AV1 case is marked expected-failure only after actual no-picture playback and error reporting have been observed; it runs normally if a future backend decodes AV1. See `VERIFICATION.md` for executed results and limitations.

## Manual Windows checklist

- [ ] Import your own MP4/H.264/AAC clip: check actual picture and speaker/headphone sound.
- [ ] Check lip sync at the beginning and after several minutes, pausing and seeking forward/backward.
- [ ] Check seek accuracy, volume, mute/unmute, repeat-one/all/off, and shuffle on mixed playlists.
- [ ] Enter/exit fullscreen with the button and double-click, then Escape; verify position and paused picture are retained and audio never doubles.
- [ ] Play audio -> video -> audio, including video-only files; ensure stale pictures clear and audio remains correct.
- [ ] Browse/search while video plays; hide/show video; use list/grid, sorting, favourites, and the Queue panel/dialog.
- [ ] Test Windows scaling at 100%, 125%, 150%, and 200%, including 800x600 and maximized windows; verify controls remain usable.
- [ ] Scroll your full real library rapidly and check lazy thumbnails, especially on slower/removable disks.
- [ ] Import via native Open files, folder picker, and local-file drag/drop; check recursive duplicates and error Details.
- [ ] Try corrupt, unsupported, moved, and deleted files during automatic playlist advancement.
- [ ] Restart: verify old imports, favourites, renamed mixed playlists/order, history, volume, mute, shuffle/repeat, window size, and panel state. Confirm startup remains silent.
- [ ] Modify a source file and request its artwork again (reopen its view or replay it); verify the cached thumbnail refreshes.

No manual checklist item is implied complete by the automated results.
