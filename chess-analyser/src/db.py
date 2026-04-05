import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'games.db')


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS games (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            platform      TEXT NOT NULL,
            game_id       TEXT UNIQUE NOT NULL,
            date          INTEGER,
            color         TEXT,
            outcome       TEXT,
            opening_name  TEXT,
            opening_eco   TEXT,
            time_control  TEXT,
            pgn           TEXT
        )
    ''')
    conn.commit()
    conn.close()
