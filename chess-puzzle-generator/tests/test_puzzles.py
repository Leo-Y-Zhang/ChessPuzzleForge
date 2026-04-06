"""
Tests for the chess puzzle generator.

Run from the project root:
    pytest tests/
"""
import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Redirect DB to temp file before any imports
import db as db_module
_tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
_tmp.close()
db_module.DB_PATH = _tmp.name

import chess
import pytest
from engine import evaluate, best_move, minimax, PIECE_VALUES
from themes import detect_theme
from generate import find_puzzle, _extract_solution
from db import init_db, save_puzzle, get_puzzle, get_random_puzzle, count_puzzles, record_attempt, get_stats


@pytest.fixture(autouse=True)
def fresh_db():
    conn = db_module.get_connection()
    conn.execute('DROP TABLE IF EXISTS progress')
    conn.execute('DROP TABLE IF EXISTS puzzles')
    conn.commit()
    conn.close()
    init_db()
    yield


# ── Engine tests ──────────────────────────────────────────────────────────────

def test_evaluate_starting_position():
    assert evaluate(chess.Board()) == 0


def test_evaluate_white_up_a_queen():
    board = chess.Board()
    board.remove_piece_at(chess.D8)
    assert evaluate(board) > 800


def test_evaluate_checkmate_score():
    board = chess.Board()
    for san in ['f3', 'e5', 'g4', 'Qh4']:
        board.push_san(san)
    assert board.is_checkmate()
    assert evaluate(board) == -20000


def test_best_move_finds_mate_in_one():
    board = chess.Board('k7/8/1K6/8/8/8/8/R7 w - - 0 1')
    move = best_move(board, depth=1)
    assert move is not None
    board.push(move)
    assert board.is_checkmate()


def test_minimax_depth_zero():
    board = chess.Board()
    assert minimax(board, 0, -float('inf'), float('inf'), True) == evaluate(board)


# ── Theme detection ───────────────────────────────────────────────────────────

def test_theme_mate_in_1():
    board = chess.Board('k7/8/1K6/8/8/8/8/R7 w - - 0 1')
    # Dynamically find the mating move so the test doesn't hardcode UCI
    mating_move = best_move(board, depth=1)
    assert mating_move is not None
    solution = [mating_move.uci()]
    assert detect_theme(board, solution) == 'mate_in_1'


def test_theme_fork():
    # Knight on d5 attacks king on e7 and rook on c7 — fork
    board = chess.Board('4k3/2r5/8/3N4/8/8/8/4K3 w - - 0 1')
    solution = ['d5e7']
    theme = detect_theme(board, solution)
    # Nxe7 forks king and rook
    assert theme in ('fork', 'tactics', 'discovered_attack')


def test_theme_empty_solution():
    assert detect_theme(chess.Board(), []) == 'tactics'


def test_theme_hanging_piece():
    # White captures an undefended rook
    board = chess.Board('k7/8/8/8/8/8/4r3/4B2K w - - 0 1')
    solution = ['e1e2']  # Bxe2, capturing free rook
    theme = detect_theme(board, solution)
    assert theme in ('hanging_piece', 'tactics')


# ── find_puzzle() ─────────────────────────────────────────────────────────────

def test_find_puzzle_detects_mate_in_one():
    board = chess.Board('k7/8/1K6/8/8/8/8/R7 w - - 0 1')
    is_puz, move, solution, score = find_puzzle(board, depth=1)
    assert is_puz is True
    assert move is not None
    b = chess.Board('k7/8/1K6/8/8/8/8/R7 w - - 0 1')
    b.push(move)
    assert b.is_checkmate()


def test_find_puzzle_rejects_starting_position():
    """The starting position has no clear tactical shot."""
    board = chess.Board()
    is_puz, move, solution, score = find_puzzle(board, depth=2)
    assert is_puz is False


def test_extract_solution_mate_in_one():
    board = chess.Board('k7/8/1K6/8/8/8/8/R7 w - - 0 1')
    move = chess.Move.from_uci('a1a8')
    solution = _extract_solution(board, move, depth=3)
    assert solution[0] == 'a1a8'
    assert len(solution) == 1  # Mate — no response needed


# ── DB tests ──────────────────────────────────────────────────────────────────

def test_save_and_retrieve():
    saved = save_puzzle(
        fen='k7/8/1K6/8/8/8/8/R7 w - - 0 1',
        solution=['a1a8'],
        theme='mate_in_1',
        rating=700
    )
    assert saved is True
    assert count_puzzles() == 1
    puzzle = get_random_puzzle()
    assert puzzle is not None
    assert puzzle['solution'] == ['a1a8']
    assert puzzle['theme'] == 'mate_in_1'
    assert puzzle['rating'] == 700


def test_duplicate_rejected():
    fen = 'k7/8/1K6/8/8/8/8/R7 w - - 0 1'
    save_puzzle(fen=fen, solution=['a1a8'], theme='mate_in_1', rating=700)
    second = save_puzzle(fen=fen, solution=['a1a8'], theme='mate_in_1', rating=700)
    assert second is False
    assert count_puzzles() == 1


def test_get_puzzle_by_id():
    save_puzzle(fen='k7/8/1K6/8/8/8/8/R7 w - - 0 1',
                solution=['a1a8'], theme='mate_in_1', rating=700)
    puzzle = get_random_puzzle()
    fetched = get_puzzle(puzzle['id'])
    assert fetched['fen'] == puzzle['fen']


def test_record_attempt_updates_stats():
    save_puzzle(fen='k7/8/1K6/8/8/8/8/R7 w - - 0 1',
                solution=['a1a8'], theme='mate_in_1', rating=700)
    puzzle = get_random_puzzle()
    record_attempt(puzzle['id'], solved=True)
    stats = get_stats()
    assert stats['solved_puzzles'] == 1
    assert stats['total_attempts'] == 1


def test_stats_empty():
    stats = get_stats()
    assert stats['total_puzzles'] == 0
    assert stats['solved_puzzles'] == 0
    assert stats['total_attempts'] == 0


def test_stats_by_theme():
    save_puzzle(fen='k7/8/1K6/8/8/8/8/R7 w - - 0 1',
                solution=['a1a8'], theme='mate_in_1', rating=700)
    save_puzzle(fen='k7/8/8/8/8/8/4r3/4B2K w - - 0 1',
                solution=['e1e2'], theme='hanging_piece', rating=800)
    stats = get_stats()
    assert stats['by_theme']['mate_in_1'] == 1
    assert stats['by_theme']['hanging_piece'] == 1
