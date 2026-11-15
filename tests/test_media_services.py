import os
import random
import sqlite3
import pytest
from retromind.repository import Repository
from retromind.queue_service import PlayQueue
from retromind.services import ImportService, read_metadata
from retromind.artwork import cache_key, image_for_media
from media_fixtures import make_video


def test_v1_migration_is_additive_and_idempotent(tmp_path):
    path = tmp_path / 'old.sqlite3'
    with sqlite3.connect(path) as db:
        db.executescript("""
        CREATE TABLE tracks(id INTEGER PRIMARY KEY,path TEXT NOT NULL UNIQUE,title TEXT NOT NULL,
            artist TEXT NOT NULL DEFAULT '',album TEXT NOT NULL DEFAULT '',duration REAL NOT NULL DEFAULT 0,favourite INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE playlists(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE);
        CREATE TABLE playlist_tracks(playlist_id INTEGER,track_id INTEGER,position INTEGER,PRIMARY KEY(playlist_id,track_id),UNIQUE(playlist_id,position));
        CREATE TABLE settings(key TEXT PRIMARY KEY,value TEXT NOT NULL);
        CREATE TABLE history(id INTEGER PRIMARY KEY,track_id INTEGER,played_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        INSERT INTO tracks VALUES(42,'old.wav','Kept','Artist','Album',12,1);
        INSERT INTO playlists VALUES(9,'Kept playlist');
        INSERT INTO playlist_tracks VALUES(9,42,4);
        INSERT INTO settings VALUES('volume','0.23');
        INSERT INTO settings VALUES('playlist','9');
        INSERT INTO history(id,track_id) VALUES(7,42);
        PRAGMA user_version=1;
        """)
    for _ in range(2):
        repo = Repository(path)
        track = repo.track(42)
        assert (track['title'],track['artist'],track['album'],track['duration'],track['favourite']) == ('Kept','Artist','Album',12,1)
        assert track['media_type'] == 'audio'
        assert track['width'] is None and track['video_codec'] is None
        assert track['date_added'] == ''  # Historical import time is unknown.
        assert repo.tracks(playlist_id=9)[0]['id'] == 42
        assert repo.setting('volume') == '0.23' and repo.setting('playlist') == '9'
        with repo.connect() as db:
            assert tuple(db.execute('SELECT id,track_id FROM history').fetchone()) == (7,42)
            assert db.execute('SELECT position FROM playlist_tracks').fetchone()[0] == 4
            assert db.execute('PRAGMA user_version').fetchone()[0] == 2


def test_future_database_version_rejected_without_modification(tmp_path):
    path = tmp_path / 'future.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('PRAGMA user_version=99')
    before = path.read_bytes()
    with pytest.raises(RuntimeError, match='newer'):
        Repository(path)
    assert before == path.read_bytes()


def test_mixed_import_duplicates_filters_order_and_rename(tmp_path):
    from test_services import wav
    audio = wav(tmp_path / 'music.wav')
    video = make_video(tmp_path / 'video.mp4')
    repo = Repository(tmp_path / 'library.sqlite3')
    service = ImportService(repo)
    result = service.import_paths([audio, video, audio.parent / '.' / audio.name])
    assert (result['added'],result['duplicates'],result['errors']) == (2,1,[])
    audio_row, = repo.tracks(media_type='audio')
    video_row, = repo.tracks(media_type='video')
    assert (video_row['width'],video_row['height']) == (160,96)
    assert video_row['video_codec'] == 'h264' and video_row['audio_codec'] == 'aac'
    assert video_row['has_video'] and video_row['has_audio'] and video_row['date_added']
    playlist = repo.create_playlist('Mixed')
    for row in (video_row, audio_row):
        repo.add_to_playlist(playlist,row['id'])
    assert [t['media_type'] for t in repo.tracks(playlist_id=playlist)] == ['video','audio']
    repo.move_in_playlist(playlist,audio_row['id'],-1)
    repo.rename_playlist(playlist,'Renamed')
    restored = Repository(repo.path)
    assert [t['media_type'] for t in restored.tracks(playlist_id=playlist)] == ['audio','video']
    assert restored.playlists()[0]['name'] == 'Renamed'
    assert [t['id'] for t in restored.tracks(sort='date_added')] == [video_row['id'],audio_row['id']]
    repo.record_play(video_row['id'])
    repo.record_play(audio_row['id'])
    assert [t['id'] for t in repo.tracks(view='recently_played')] == [audio_row['id'],video_row['id']]


def test_stream_information_overrides_extension(tmp_path):
    from test_services import wav
    audio = wav(tmp_path / 'not_video.mp4')
    assert read_metadata(audio)['media_type'] == 'audio'
    video = make_video(tmp_path / 'video.mp4',audio_codec=None)
    metadata = read_metadata(video)
    assert metadata['has_video'] and not metadata['has_audio']
    assert metadata['audio_codec'] is None


def test_video_thumbnail_and_source_change_invalidation(tmp_path):
    video = make_video(tmp_path / 'video.mp4', audio_codec=None)
    before = cache_key(video)
    image = image_for_media(video)
    assert not image.isNull() and image.width() == 160 and image.height() == 96
    assert image.pixelColor(10,10).red() > 150
    stat = video.stat()
    os.utime(video, ns=(stat.st_atime_ns,stat.st_mtime_ns+1_000_000))
    assert cache_key(video) != before


def test_shuffle_repeat_and_queue_editing():
    queue = PlayQueue(rng=random.Random(5))
    queue.start([1,2,3,4],2)
    queue.set_shuffle(True)
    assert queue.current == 2 and queue.index == 0
    assert set(queue.items) == {1,2,3,4}
    queue.set_shuffle(False)
    assert queue.items == [1,2,3,4] and queue.current == 2
    queue.remove(3)
    assert queue.upcoming == [4]
    queue.repeat = 'one'
    assert queue.advance(automatic=True) == 2
    assert queue.advance(automatic=False) == 4
    queue.repeat = 'off'
    assert queue.advance(automatic=True) is None
    queue.repeat = 'all'
    assert queue.advance(automatic=True) == 1
    queue.select(4)
    assert queue.current == 4
    queue.remove(4)
    assert queue.current == 4  # Current source cannot be removed mid-play.
