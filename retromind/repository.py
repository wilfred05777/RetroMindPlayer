"""SQLite repository. Each operation owns its connection, including in workers."""
import sqlite3
from pathlib import Path


class Repository:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            if db.execute('PRAGMA user_version').fetchone()[0] > 1:
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
                PRAGMA user_version=1;
            """)

    def connect(self):
        # Explicit close is handled by Connection below; sqlite's own context manager
        # commits/rolls back but does not close the connection.
        return Connection(self.path)

    def add_track(self, metadata):
        with self.connect() as db:
            cursor = db.execute('INSERT OR IGNORE INTO tracks(path,title,artist,album,duration) VALUES(?,?,?,?,?)',
                                tuple(metadata[k] for k in ('path', 'title', 'artist', 'album', 'duration')))
            return cursor.rowcount == 1

    def tracks(self, query='', favourites=False, playlist_id=0):
        sql = 'SELECT t.* FROM tracks t'
        args = []
        if playlist_id:
            sql += ' JOIN playlist_tracks p ON p.track_id=t.id'
        sql += ' WHERE 1=1'
        if playlist_id:
            sql += ' AND p.playlist_id=?'
            args.append(playlist_id)
        if favourites:
            sql += ' AND t.favourite=1'
        if query:
            sql += " AND (instr(lower(t.title),lower(?))>0 OR instr(lower(t.artist),lower(?))>0 OR instr(lower(t.album),lower(?))>0)"
            args.extend([query] * 3)
        sql += ' ORDER BY p.position' if playlist_id else ' ORDER BY t.title COLLATE NOCASE,t.id'
        with self.connect() as db:
            return [dict(row) for row in db.execute(sql, args)]

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
