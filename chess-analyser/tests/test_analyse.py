"""
Unit tests for the chess analyser.

Run from the project root:
    pytest tests/
"""
import sys
import os
import itertools
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Redirect the DB to a temp file before importing anything else
import db as db_module
_tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_tmp.close()
db_module.DB_PATH = _tmp.name

from db import init_db, get_connection
from analyse import get_stats, _pct

# Auto-incrementing game ID so every inserted row is unique
_id_counter = itertools.count(1)


def _next_id():
    return str(next(_id_counter))


def _insert(**kwargs):
    defaults = dict(
        platform='lichess', game_id=_next_id(), date=1700000000,
        color='white', outcome='win',
        opening_name='Sicilian Defence', opening_eco='B20',
        time_control='rapid', pgn=''
    )
    defaults.update(kwargs)
    if 'game_id' not in kwargs:
        defaults['game_id'] = _next_id()
    conn = get_connection()
    conn.execute('''
        INSERT INTO games
        (platform, game_id, date, color, outcome, opening_name, opening_eco, time_control, pgn)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        defaults['platform'], defaults['game_id'], defaults['date'],
        defaults['color'], defaults['outcome'], defaults['opening_name'],
        defaults['opening_eco'], defaults['time_control'], defaults['pgn']
    ))
    conn.commit()
    conn.close()


import pytest

@pytest.fixture(autouse=True)
def fresh_db():
    """Wipe and recreate the games table before every test."""
    conn = get_connection()
    conn.execute('DROP TABLE IF EXISTS games')
    conn.commit()
    conn.close()
    init_db()
    yield


# ── _pct helper ────────────────────────────────────────────────────────────────

def test_pct_basic():
    assert _pct(1, 4) == 25.0

def test_pct_zero_denominator():
    assert _pct(0, 0) == 0.0

def test_pct_all_wins():
    assert _pct(5, 5) == 100.0

def test_pct_rounding():
    assert _pct(1, 3) == 33.3


# ── get_stats() with empty DB ──────────────────────────────────────────────────

def test_empty_db_returns_total_zero():
    stats = get_stats()
    assert stats['total_games'] == 0


# ── Win rate ───────────────────────────────────────────────────────────────────

def test_win_rate_two_wins_one_loss():
    _insert(outcome='win')
    _insert(outcome='win')
    _insert(outcome='loss')
    stats = get_stats()
    assert stats['total_games'] == 3
    assert stats['win_rate'] == pytest.approx(66.7, abs=0.1)


def test_draw_counted_in_total_not_in_wins():
    _insert(outcome='win')
    _insert(outcome='draw')
    _insert(outcome='loss')
    stats = get_stats()
    assert stats['total_games'] == 3
    assert stats['overall'].get('draw', 0) == 1
    assert stats['win_rate'] == pytest.approx(33.3, abs=0.1)


# ── By colour ─────────────────────────────────────────────────────────────────

def test_by_color_win_rates():
    _insert(color='white', outcome='win')
    _insert(color='white', outcome='loss')
    _insert(color='black', outcome='win')
    _insert(color='black', outcome='win')
    stats = get_stats()
    assert stats['by_color']['white']['total'] == 2
    assert stats['by_color']['white']['win_rate'] == 50.0
    assert stats['by_color']['black']['win_rate'] == 100.0


def test_by_color_totals_correct():
    for _ in range(3):
        _insert(color='white', outcome='win')
    for _ in range(2):
        _insert(color='black', outcome='loss')
    stats = get_stats()
    assert stats['by_color']['white']['total'] == 3
    assert stats['by_color']['black']['total'] == 2


# ── Top openings ──────────────────────────────────────────────────────────────

def test_top_openings_counts():
    for _ in range(4):
        _insert(opening_name='Sicilian Defence', outcome='win')
    for _ in range(2):
        _insert(opening_name='French Defence', outcome='loss')
    stats = get_stats()
    by_name = {o['name']: o for o in stats['top_openings']}
    assert by_name['Sicilian Defence']['total'] == 4
    assert by_name['Sicilian Defence']['wins'] == 4
    assert by_name['French Defence']['losses'] == 2


def test_top_openings_limited_to_12():
    for i in range(15):
        _insert(opening_name=f'Opening {i}', outcome='win')
    stats = get_stats()
    assert len(stats['top_openings']) <= 12


def test_unknown_opening_excluded():
    _insert(opening_name='Unknown', outcome='win')
    _insert(opening_name='Sicilian Defence', outcome='win')
    stats = get_stats()
    names = [o['name'] for o in stats['top_openings']]
    assert 'Unknown' not in names


# ── Time control ──────────────────────────────────────────────────────────────

def test_by_time_control():
    _insert(time_control='blitz', outcome='win')
    _insert(time_control='blitz', outcome='loss')
    _insert(time_control='rapid', outcome='win')
    stats = get_stats()
    by_tc = {t['control']: t for t in stats['by_time_control']}
    assert by_tc['blitz']['total'] == 2
    assert by_tc['rapid']['total'] == 1
    assert by_tc['blitz']['win_rate'] == 50.0


# ── Over time ─────────────────────────────────────────────────────────────────

def test_over_time_groups_by_month():
    # All on the same timestamp (same month)
    _insert(date=1700000000)
    _insert(date=1700000000)
    _insert(date=1700000000)
    stats = get_stats()
    assert len(stats['over_time']) == 1
    assert stats['over_time'][0]['total'] == 3


def test_over_time_win_rate():
    _insert(date=1700000000, outcome='win')
    _insert(date=1700000000, outcome='loss')
    stats = get_stats()
    assert stats['over_time'][0]['win_rate'] == 50.0
