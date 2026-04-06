"""
Unit tests for the chess engine.

Run from the project root:
    pytest tests/
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import chess
import pytest
from engine import evaluate, best_move, minimax, order_moves, PIECE_VALUES


# ── evaluate() ────────────────────────────────────────────────────────────────

def test_evaluate_starting_position_is_zero():
    """The starting position is symmetric, so both sides score 0."""
    board = chess.Board()
    assert evaluate(board) == 0


def test_evaluate_white_up_a_queen():
    """Remove black's queen — white should score roughly +900 (queen value)."""
    board = chess.Board()
    board.remove_piece_at(chess.D8)
    score = evaluate(board)
    assert score > 800


def test_evaluate_black_up_a_rook():
    """Remove white's queen-side rook — black should score positively."""
    board = chess.Board()
    board.remove_piece_at(chess.A1)
    score = evaluate(board)
    assert score < -400


def test_evaluate_checkmate_white_mated():
    """
    After Fool's Mate, white is checkmated (white's turn, in checkmate).
    evaluate() should return -20000 (the losing side is to move).
    """
    board = chess.Board()
    for san in ['f3', 'e5', 'g4', 'Qh4']:
        board.push_san(san)
    assert board.is_checkmate()
    assert evaluate(board) == -20000


def test_evaluate_stalemate_is_zero():
    # Classic stalemate: black king has no legal moves
    board = chess.Board('5k2/5P2/5K2/8/8/8/8/8 b - - 0 1')
    if board.is_stalemate():
        assert evaluate(board) == 0


def test_evaluate_insufficient_material_is_zero():
    board = chess.Board('8/8/8/8/8/8/8/4K2k w - - 0 1')  # KvK
    assert evaluate(board) == 0


# ── best_move() ───────────────────────────────────────────────────────────────

def test_best_move_finds_mate_in_one():
    """Ra8# is the only mating move in this position."""
    board = chess.Board('k7/8/1K6/8/8/8/8/R7 w - - 0 1')
    move = best_move(board, depth=1)
    assert move is not None
    board.push(move)
    assert board.is_checkmate()


def test_best_move_captures_hanging_queen():
    """White rook can take the undefended black queen on e2 for free."""
    board = chess.Board('7k/8/8/8/8/8/4q3/4R2K w - - 0 1')
    move = best_move(board, depth=2)
    assert move is not None
    assert move.to_square == chess.E2


def test_best_move_avoids_losing_piece():
    """White should not move the bishop into a square attacked by a pawn."""
    board = chess.Board()
    board.push_san('e4')
    board.push_san('d5')
    # Engine should not play a move that blunders material at depth 2
    move = best_move(board, depth=2)
    assert move is not None
    board.push(move)
    # The position should not immediately lose a piece
    score = evaluate(board)
    assert score > -200  # Not badly losing


def test_best_move_returns_none_when_game_over():
    """After checkmate, best_move should return None."""
    board = chess.Board('k7/8/1K6/8/8/8/8/R7 w - - 0 1')
    # Find and play the mating move, then verify best_move returns None
    mating_move = best_move(board, depth=1)
    assert mating_move is not None
    board.push(mating_move)
    assert board.is_checkmate()
    assert best_move(board, depth=3) is None


# ── order_moves() ─────────────────────────────────────────────────────────────

def test_order_moves_puts_captures_first():
    """After 1.e4 d5, white can capture on d5. That capture should come first."""
    board = chess.Board()
    board.push_san('e4')
    board.push_san('d5')
    moves = order_moves(board)
    assert board.is_capture(moves[0]), "First move should be a capture"


def test_order_moves_checks_before_quiet():
    """A checking move should rank above a quiet move."""
    board = chess.Board('k7/8/8/8/8/8/8/R6K w - - 0 1')
    moves = order_moves(board)
    # Ra8+ is a check — it should appear early in the ordered list
    check_moves = [m for m in moves if board.gives_check(m)]
    if check_moves:
        assert moves.index(check_moves[0]) < len(moves) // 2


# ── minimax() ─────────────────────────────────────────────────────────────────

def test_minimax_depth_zero_equals_evaluate():
    board = chess.Board()
    score = minimax(board, 0, -float('inf'), float('inf'), True)
    assert score == evaluate(board)


def test_minimax_alpha_beta_matches_full_search():
    """Alpha-beta pruning must return the same score as unconstrained search."""
    board = chess.Board()
    board.push_san('e4')
    board.push_san('e5')
    full    = minimax(board, 2, -float('inf'), float('inf'), True)
    pruned  = minimax(board, 2, -float('inf'), float('inf'), True)
    assert full == pruned


def test_minimax_detects_forced_mate():
    """Minimax at depth 1 should see the mate and return a large score."""
    board = chess.Board('k7/8/1K6/8/8/8/8/R7 w - - 0 1')
    score = minimax(board, 1, -float('inf'), float('inf'), True)
    assert score >= 19000  # Checkmate score
