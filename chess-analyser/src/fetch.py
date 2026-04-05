"""
fetch.py — pulls games from Lichess and Chess.com, stores them locally in SQLite.
After the first run, the dashboard works fully offline.

Usage:
    python fetch.py lichess YOUR_USERNAME
    python fetch.py chesscom YOUR_USERNAME
"""
import sys
import json
import requests
from db import init_db, get_connection


# ── Lichess ──────────────────────────────────────────────────────────────────

def fetch_lichess(username: str, max_games: int = 500) -> list:
    """Fetch games from Lichess public API. Returns list of raw game dicts."""
    url = f"https://lichess.org/api/games/user/{username}"
    params = {
        'max': max_games,
        'pgnInJson': 'true',
        'opening': 'true',
        'clocks': 'false',
        'evals': 'false'
    }
    headers = {'Accept': 'application/x-ndjson'}

    print(f"Fetching up to {max_games} games from Lichess for '{username}'...")
    response = requests.get(url, params=params, headers=headers, stream=True, timeout=30)
    response.raise_for_status()

    games = [json.loads(line) for line in response.iter_lines() if line]
    print(f"  Got {len(games)} games.")
    return games


def parse_lichess(raw: dict, username: str) -> dict:
    players = raw.get('players', {})
    white_name = players.get('white', {}).get('user', {}).get('name', '').lower()
    color = 'white' if white_name == username.lower() else 'black'

    winner = raw.get('winner')          # 'white', 'black', or absent (draw)
    status = raw.get('status', '')
    draw_statuses = {'draw', 'stalemate', 'repetition', 'insufficient', 'seventyfive', 'outoftime'}

    if winner is None or status in draw_statuses:
        outcome = 'draw'
    elif winner == color:
        outcome = 'win'
    else:
        outcome = 'loss'

    opening = raw.get('opening') or {}

    return {
        'platform':     'lichess',
        'game_id':      raw.get('id', ''),
        'date':         raw.get('createdAt', 0) // 1000,
        'color':        color,
        'outcome':      outcome,
        'opening_name': opening.get('name', 'Unknown'),
        'opening_eco':  opening.get('eco', ''),
        'time_control': raw.get('speed', 'unknown'),
        'pgn':          raw.get('pgn', '')
    }


# ── Chess.com ────────────────────────────────────────────────────────────────

def fetch_chesscom(username: str, months: int = 6) -> list:
    """Fetch recent games from Chess.com public API."""
    archives_url = f"https://api.chess.com/pub/player/{username}/games/archives"
    archives = requests.get(archives_url, timeout=10).json().get('archives', [])
    recent = archives[-months:]

    print(f"Fetching last {len(recent)} month(s) from Chess.com for '{username}'...")
    games = []
    for url in recent:
        data = requests.get(url, timeout=10).json()
        games.extend(data.get('games', []))
    print(f"  Got {len(games)} games.")
    return games


def parse_chesscom(raw: dict, username: str) -> dict:
    white = raw.get('white', {})
    black = raw.get('black', {})
    color = 'white' if white.get('username', '').lower() == username.lower() else 'black'

    white_result = white.get('result', '')
    win_results = {'win'}
    draw_results = {'agreed', 'stalemate', 'repetition', 'insufficient', '50move', 'timevsinsufficient'}

    if white_result in win_results:
        outcome = 'win' if color == 'white' else 'loss'
    elif white_result in draw_results:
        outcome = 'draw'
    else:
        outcome = 'loss' if color == 'white' else 'win'

    opening = raw.get('opening') or {}
    end_time = raw.get('end_time', 0)
    time_class = raw.get('time_class', 'unknown')

    return {
        'platform':     'chesscom',
        'game_id':      str(raw.get('url', '')).split('/')[-1],
        'date':         end_time,
        'color':        color,
        'outcome':      outcome,
        'opening_name': opening.get('name', 'Unknown'),
        'opening_eco':  opening.get('eco', ''),
        'time_control': time_class,
        'pgn':          raw.get('pgn', '')
    }


# ── Storage ──────────────────────────────────────────────────────────────────

def save_games(parsed_games: list):
    conn = get_connection()
    saved = 0
    for g in parsed_games:
        try:
            conn.execute('''
                INSERT OR IGNORE INTO games
                (platform, game_id, date, color, outcome, opening_name, opening_eco, time_control, pgn)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (g['platform'], g['game_id'], g['date'], g['color'], g['outcome'],
                  g['opening_name'], g['opening_eco'], g['time_control'], g['pgn']))
            saved += conn.execute('SELECT changes()').fetchone()[0]
        except Exception as e:
            print(f"  Warning: could not save game {g.get('game_id')}: {e}")
    conn.commit()
    conn.close()
    print(f"  Saved {saved} new games to database.")


# ── Entry point ───────────────────────────────────────────────────────────────

def run(platform: str, username: str):
    init_db()
    if platform == 'lichess':
        raw = fetch_lichess(username)
        parsed = [parse_lichess(g, username) for g in raw]
    elif platform == 'chesscom':
        raw = fetch_chesscom(username)
        parsed = [parse_chesscom(g, username) for g in raw]
    else:
        print(f"Unknown platform '{platform}'. Use 'lichess' or 'chesscom'.")
        return
    save_games(parsed)
    print("Done. Run app.py to view your dashboard.")


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python fetch.py [lichess|chesscom] USERNAME")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])
