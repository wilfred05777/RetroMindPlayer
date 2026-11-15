"""SQLite repository. Each operation owns its connection, including in workers."""
import sqlite3
from pathlib import Path


class Repository:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            if db.execute('PRAGMA user_version').fetchone()[0] > 2:
                raise RuntimeError('This library was created by a newer RetroMind version.')
            db.executescript("""
                CREATE TABLE IF NOT EXISTS tracks (
                    id INTEGER PRIMARY KEY, path TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL, artist TEXT NOT NULL DEFAULT '',
                    album TEXT NOT NULL DEFAULT '', duration REAL NOT NULL DEFAULT 0,
                    favourite INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS playlists (
                    id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE);
                CREATE TABLE IF NOT EXISTS playlist_tracks (
                    playlist_id INTEGER NOT NULL REFERENCES playlists(id) ON DELETE CASCADE,
                    track_id INTEGER NOT NULL REFERENCES tracks(id) ON DELETE CASCADE,
                    position INTEGER NOT NULL,
                    PRIMARY KEY (playlist_id, track_id), UNIQUE (playlist_id, position));
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY, track_id INTEGER NOT NULL REFERENCES tracks(id),
                    played_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
            """)
            # Additive migration: retain all original IDs, ordering, history and settings.
            db.execute('BEGIN IMMEDIATE')
            columns = {row['name'] for row in db.execute('PRAGMA table_info(tracks)')}
            additions = {'media_type': "TEXT NOT NULL DEFAULT 'audio'",
                         'date_added': "TEXT NOT NULL DEFAULT ''",
                         'width': 'INTEGER', 'height': 'INTEGER',
                         'video_codec': 'TEXT', 'audio_codec': 'TEXT',
                         'container': 'TEXT', 'has_audio': 'INTEGER',
                         'has_video': 'INTEGER'}
            for name, definition in additions.items():
                if name not in columns:
                    db.execute(f'ALTER TABLE tracks ADD COLUMN {name} {definition}')
            db.execute('CREATE INDEX IF NOT EXISTS history_track_time ON history(track_id,played_at)')
            db.execute('PRAGMA user_version=2')

    def connect(self):
        # Explicit close is handled by Connection below; sqlite's own context manager
        # commits/rolls back but does not close the connection.
        return Connection(self.path)

    def add_track(self, metadata):
        names = ('path', 'title', 'artist', 'album', 'duration', 'media_type',
                 'width', 'height', 'video_codec', 'audio_codec', 'container', 'has_audio', 'has_video')
        defaults = dict(artist='', album='', duration=0, media_type='audio')
        values = [metadata.get(key, defaults.get(key)) for key in names]
        with self.connect() as db:
            cursor = db.execute('INSERT OR IGNORE INTO tracks(' + ','.join(names) +
                                ',date_added) VALUES(' + ','.join('?' for _ in names) + ',CURRENT_TIMESTAMP)', values)
            return cursor.rowcount == 1

    def tracks(self, query='', favourites=False, playlist_id=0, media_type='all', sort='title', view='all', limit=None):
        sql = 'SELECT t.* FROM tracks t'
        args = []
        if playlist_id:
            sql += ' JOIN playlist_tracks p ON p.track_id=t.id'
        if view == 'recently_played':
            sql += ' JOIN (SELECT track_id,MAX(id) latest FROM history GROUP BY track_id) h ON h.track_id=t.id'
        sql += ' WHERE 1=1'
        if playlist_id:
            sql += ' AND p.playlist_id=?'
            args.append(playlist_id)
        if favourites or view == 'favourites':
            sql += ' AND t.favourite=1'
        if media_type in ('audio', 'video'):
            sql += ' AND t.media_type=?'
            args.append(media_type)
        if query:
            sql += " AND (instr(lower(t.title),lower(?))>0 OR instr(lower(t.artist),lower(?))>0 OR instr(lower(t.album),lower(?))>0)"
            args.extend([query] * 3)
        orders = {'title': 't.title COLLATE NOCASE,t.id', 'artist': 't.artist COLLATE NOCASE,t.title COLLATE NOCASE,t.id',
                  'date_added': 't.date_added DESC,t.id DESC', 'duration': 't.duration DESC,t.id'}
        order = 'p.position' if playlist_id and sort == 'title' else orders.get(sort, orders['title'])
        if view == 'recently_added':
            order = orders['date_added']
        elif view == 'recently_played':
            order = 'h.latest DESC'
        sql += ' ORDER BY ' + order
        if limit is not None:
            sql += ' LIMIT ?'
            args.append(max(0, int(limit)))
        with self.connect() as db:
            return [dict(row) for row in db.execute(sql, args)]

    def tracks_by_ids(self, ids):
        ids = list(ids)
        found = {}
        with self.connect() as db:
            for start in range(0, len(ids), 900):
                chunk = ids[start:start + 900]
                placeholders = ','.join('?' for _ in chunk)
                for row in db.execute('SELECT * FROM tracks WHERE id IN (' + placeholders + ')', chunk):
                    found[row['id']] = dict(row)
        return [found[track_id] for track_id in ids if track_id in found]

    def rename_playlist(self, playlist_id, name):
        name = name.strip()
        if not name:
            raise ValueError('Enter a playlist name.')
        with self.connect() as db:
            try:
                db.execute('UPDATE playlists SET name=? WHERE id=?', (name, playlist_id))
            except sqlite3.IntegrityError as error:
                raise ValueError('A playlist with that name already exists.') from error

    def track(self, track_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM tracks WHERE id=?', (track_id,)).fetchone()
            return dict(row) if row else None

    def favourite(self, track_id):
        with self.connect() as db:
            db.execute('UPDATE tracks SET favourite=1-favourite WHERE id=?', (track_id,))

    def playlists(self):
        with self.connect() as db:
            return [dict(row) for row in db.execute('SELECT * FROM playlists ORDER BY name COLLATE NOCASE')]

    def create_playlist(self, name):
        name = name.strip()
        if not name:
            raise ValueError('Enter a playlist name.')
        with self.connect() as db:
            try:
                return db.execute('INSERT INTO playlists(name) VALUES(?)', (name,)).lastrowid
            except sqlite3.IntegrityError as error:
                raise ValueError('A playlist with that name already exists.') from error

    def add_to_playlist(self, playlist_id, track_id):
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO playlist_tracks(playlist_id,track_id,position) SELECT ?,?,COALESCE(MAX(position),-1)+1 FROM playlist_tracks WHERE playlist_id=?',
                       (playlist_id, track_id, playlist_id))

    def remove_from_playlist(self, playlist_id, track_id):
        with self.connect() as db:
            db.execute('DELETE FROM playlist_tracks WHERE playlist_id=? AND track_id=?', (playlist_id, track_id))

    def move_in_playlist(self, playlist_id, track_id, direction):
        with self.connect() as db:
            rows = db.execute('SELECT track_id,position FROM playlist_tracks WHERE playlist_id=? ORDER BY position', (playlist_id,)).fetchall()
            index = next((i for i, row in enumerate(rows) if row['track_id'] == track_id), -1)
            other = index + direction
            if index < 0 or other < 0 or other >= len(rows):
                return
            a, b = rows[index], rows[other]
            db.execute('UPDATE playlist_tracks SET position=-1 WHERE playlist_id=? AND track_id=?', (playlist_id, a['track_id']))
            db.execute('UPDATE playlist_tracks SET position=? WHERE playlist_id=? AND track_id=?', (a['position'], playlist_id, b['track_id']))
            db.execute('UPDATE playlist_tracks SET position=? WHERE playlist_id=? AND track_id=?', (b['position'], playlist_id, a['track_id']))

    def setting(self, key, default=''):
        with self.connect() as db:
            row = db.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
            return row['value'] if row else default

    def save_setting(self, key, value):
        with self.connect() as db:
            db.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, str(value)))

    def record_play(self, track_id):
        with self.connect() as db:
            db.execute('INSERT INTO history(track_id) VALUES(?)', (track_id,))


class Connection(sqlite3.Connection):
    def __init__(self, path):
        super().__init__(path, timeout=15)
        self.row_factory = sqlite3.Row
        self.execute('PRAGMA foreign_keys=ON')

    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()
