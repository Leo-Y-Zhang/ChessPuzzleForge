"""Mate-in-3: the engine's exhaustive forced-mate search generalises to depth 3.

forced_mate_move is already general-depth, so this pins that it genuinely finds a
FORCED mate in three (every defence loses in <= 3) and that the new bank puzzle
and the verifier's mate_in_3 branch agree.
"""

from palamedes.engine import Board, forced_mate_move, move_from_uci
from palamedes.fen_bank import get_puzzle
from palamedes.verifier import _move_forces_mate, verify_puzzle, verify_solution

MATE3_FEN = "8/8/8/8/8/6k1/1R6/R5K1 w - - 0 1"
MATE1_FEN = "6k1/5ppp/8/8/8/8/8/R6K w - - 0 1"  # Ra8#
BARE_KINGS = "4k3/8/4K3/8/8/8/8/8 w - - 0 1"


def test_forced_mate_move_finds_a_forced_mate_in_3():
    board = Board.from_fen(MATE3_FEN)
    key = forced_mate_move(board, 3)
    assert key is not None
    assert _move_forces_mate(board, move_from_uci(board, key), 3)


def test_it_is_genuinely_three_not_two():
    board = Board.from_fen(MATE3_FEN)
    assert forced_mate_move(board, 2) is None
    key = forced_mate_move(board, 3)
    assert not _move_forces_mate(board, move_from_uci(board, key), 2)


def test_forced_mate_is_monotone_over_depth():
    board = Board.from_fen(MATE1_FEN)
    assert forced_mate_move(board, 1) is not None
    assert forced_mate_move(board, 3) is not None


def test_no_mate_position_returns_none():
    assert forced_mate_move(Board.from_fen(BARE_KINGS), 3) is None


def test_verifier_mate_in_3_branch():
    ok, message = verify_solution(get_puzzle("m3-two-rook-ladder"), "b2b4")
    assert ok, message


def test_bank_mate_in_3_puzzle_verifies():
    ok, message = verify_puzzle(get_puzzle("m3-two-rook-ladder"))
    assert ok, message
