import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'puzzles.db')


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS puzzles (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            fen      TEXT UNIQUE NOT NULL,
            solution TEXT NOT NULL,
            theme    TEXT NOT NULL,
            rating   INTEGER NOT NULL DEFAULT 1000,
            created  INTEGER DEFAULT (strftime('%s','now'))
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS progress (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            puzzle_id INTEGER NOT NULL REFERENCES puzzles(id),
            solved    INTEGER NOT NULL DEFAULT 0,
            timestamp INTEGER DEFAULT (strftime('%s','now'))
        )
    ''')
    conn.commit()
    conn.close()


def save_puzzle(fen: str, solution: list, theme: str, rating: int) -> bool:
    """Save a puzzle. Returns True if new, False if already exists (deduped by FEN)."""
    conn = get_connection()
    if conn.execute('SELECT id FROM puzzles WHERE fen = ?', (fen,)).fetchone():
        conn.close()
        return False
    conn.execute(
        'INSERT INTO puzzles (fen, solution, theme, rating) VALUES (?, ?, ?, ?)',
        (fen, json.dumps(solution), theme, rating)
    )
    conn.commit()
    conn.close()
    return True


def count_puzzles() -> int:
    conn = get_connection()
    n = conn.execute('SELECT COUNT(*) FROM puzzles').fetchone()[0]
    conn.close()
    return n


def get_puzzle(puzzle_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute('SELECT * FROM puzzles WHERE id = ?', (puzzle_id,)).fetchone()
    conn.close()
    return _row_to_dict(row)


def get_random_puzzle(theme: str = None) -> dict | None:
    conn = get_connection()
    if theme and theme != 'all':
        row = conn.execute(
            'SELECT * FROM puzzles WHERE theme = ? ORDER BY RANDOM() LIMIT 1', (theme,)
        ).fetchone()
    else:
        row = conn.execute('SELECT * FROM puzzles ORDER BY RANDOM() LIMIT 1').fetchone()
    conn.close()
    return _row_to_dict(row)


def get_next_unsolved(theme: str = None) -> dict | None:
    """Return a puzzle the user hasn't solved yet, if any remain."""
    conn = get_connection()
    solved_ids = {
        r[0] for r in conn.execute(
            'SELECT puzzle_id FROM progress WHERE solved = 1'
        ).fetchall()
    }
    if theme and theme != 'all':
        rows = conn.execute(
            'SELECT * FROM puzzles WHERE theme = ? ORDER BY rating', (theme,)
        ).fetchall()
    else:
        rows = conn.execute('SELECT * FROM puzzles ORDER BY rating').fetchall()
    conn.close()
    for row in rows:
        if row['id'] not in solved_ids:
            return _row_to_dict(row)
    # All solved — fall back to random
    return get_random_puzzle(theme)


def record_attempt(puzzle_id: int, solved: bool):
    conn = get_connection()
    conn.execute(
        'INSERT INTO progress (puzzle_id, solved) VALUES (?, ?)',
        (puzzle_id, 1 if solved else 0)
    )
    conn.commit()
    conn.close()


def get_stats() -> dict:
    conn = get_connection()
    total = conn.execute('SELECT COUNT(*) FROM puzzles').fetchone()[0]
    solved = conn.execute(
        'SELECT COUNT(DISTINCT puzzle_id) FROM progress WHERE solved = 1'
    ).fetchone()[0]
    attempts = conn.execute('SELECT COUNT(*) FROM progress').fetchone()[0]
    by_theme = conn.execute(
        'SELECT theme, COUNT(*) FROM puzzles GROUP BY theme ORDER BY COUNT(*) DESC'
    ).fetchall()
    conn.close()
    return {
        'total_puzzles': total,
        'solved_puzzles': solved,
        'total_attempts': attempts,
        'by_theme': {row[0]: row[1] for row in by_theme}
    }


def _row_to_dict(row) -> dict | None:
    if row is None:
        return None
    return {
        'id': row['id'],
        'fen': row['fen'],
        'solution': json.loads(row['solution']),
        'theme': row['theme'],
        'rating': row['rating']
    }
