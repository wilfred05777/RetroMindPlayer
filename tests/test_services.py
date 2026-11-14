import wave
import pytest
from retromind.repository import Repository
from retromind.services import ImportService, canonical_path


@pytest.fixture
def repo(tmp_path):
    return Repository(tmp_path / 'data' / 'library.sqlite3')


def wav(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b'\x00\x00' * 8000)
    return path


def add(repo, path, title='Song', artist='', album=''):
    return repo.add_track(dict(path=str(path), title=title, artist=artist, album=album, duration=1))


def test_recursive_import_metadata_fallback_and_duplicates(repo, tmp_path):
    root = tmp_path / 'music'
    path = wav(root / 'nested' / 'Untagged.wav')
    (root / 'ignore.txt').write_text('not music')
    progress = []
    result = ImportService(repo).scan(root, lambda *args: progress.append(args))
    assert result == dict(added=1, duplicates=0, errors=[], cancelled=False)
    track = repo.tracks()[0]
    assert track['title'] == 'Untagged'
    assert track['duration'] == pytest.approx(1)
    assert track['path'] == canonical_path(path)
    result = ImportService(repo).scan(root / 'nested' / '..')
    assert result['added'] == 0 and result['duplicates'] == 1
    assert progress[-1][:2] == (1, 1)


def test_import_skips_corrupt_audio_and_continues(repo, tmp_path):
    wav(tmp_path / 'valid.wav')
    (tmp_path / 'broken.mp3').write_bytes(b'invalid')
    result = ImportService(repo).scan(tmp_path)
    assert result['added'] == 1
    assert len(result['errors']) == 1
    assert 'broken.mp3' in result['errors'][0]


def test_search_title_artist_album_favourites_and_sql_literals(repo):
    add(repo, 'one', 'Electric Morning', 'Nova', 'Sky')
    add(repo, 'two', "100%_' Music", 'Other', 'Moon')
    track = repo.tracks('nova')[0]
    assert repo.tracks('ELECTRIC')[0]['id'] == track['id']
    assert repo.tracks('sky')[0]['id'] == track['id']
    assert repo.tracks("%_'")[0]['path'] == 'two'
    assert repo.tracks("' OR 1=1 --") == []
    assert repo.tracks(favourites=True) == []
    repo.favourite(track['id'])
    assert len(repo.tracks(favourites=True)) == 1
    repo.favourite(track['id'])
    assert repo.tracks(favourites=True) == []


def test_playlist_append_duplicate_remove_and_reorder_persist(repo):
    for i in range(3):
        add(repo, str(i), title=str(i))
    a, b, c = [t['id'] for t in repo.tracks()]
    playlist = repo.create_playlist('Night drive')
    for track in (c, a, b, a):
        repo.add_to_playlist(playlist, track)
    ids = lambda: [t['id'] for t in repo.tracks(playlist_id=playlist)]
    assert ids() == [c, a, b]
    repo.move_in_playlist(playlist, b, -1)
    assert ids() == [c, b, a]
    repo.move_in_playlist(playlist, c, -1)
    assert ids() == [c, b, a]
    repo.remove_from_playlist(playlist, b)
    repo.add_to_playlist(playlist, b)
    assert ids() == [c, a, b]
    restored = Repository(repo.path)
    assert [t['id'] for t in restored.tracks(playlist_id=playlist)] == [c, a, b]
    with pytest.raises(ValueError):
        repo.create_playlist('Night drive')
    with pytest.raises(ValueError):
        repo.create_playlist(' ')


def test_settings_and_history_persist(repo):
    add(repo, 'song')
    track = repo.tracks()[0]
    repo.record_play(track['id'])
    repo.save_setting('volume', .4)
    restored = Repository(repo.path)
    assert restored.setting('volume') == '0.4'
    with restored.connect() as db:
        assert db.execute('SELECT track_id FROM history').fetchone()[0] == track['id']


def test_cancel_and_missing_folder(repo, tmp_path):
    wav(tmp_path / 'cancel.wav')
    assert ImportService(repo).scan(tmp_path, cancelled=lambda: True)['cancelled']
    assert repo.tracks() == []
    with pytest.raises(ValueError, match='unavailable'):
        ImportService(repo).scan(tmp_path / 'missing')


def test_wav_id3_metadata(repo, tmp_path):
    from mutagen.wave import WAVE
    from mutagen.id3 import TIT2, TPE1, TALB
    path = wav(tmp_path / 'tagged.wav')
    audio = WAVE(path)
    audio.add_tags()
    audio.tags.add(TIT2(encoding=3, text=['Tagged title']))
    audio.tags.add(TPE1(encoding=3, text=['Tagged artist']))
    audio.tags.add(TALB(encoding=3, text=['Tagged album']))
    audio.save()
    ImportService(repo).scan(tmp_path)
    track = repo.tracks()[0]
    assert (track['title'], track['artist'], track['album']) == ('Tagged title', 'Tagged artist', 'Tagged album')
