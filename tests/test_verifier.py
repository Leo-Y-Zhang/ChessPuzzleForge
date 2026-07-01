"""Verifier tests - pure standard library.  These MUST always run green."""

from __future__ import annotations

from chesspuzzle.engine import Board
from chesspuzzle.fen_bank import get_puzzle
from chesspuzzle.verifier import (
    net_material_gain,
    verify_puzzle,
    verify_solution,
)


def test_mate_in_1_correct_move_verifies():
    puzzle = get_puzzle("m1-backrank-rook")
    ok, msg = verify_solution(puzzle, "a1a8")
    assert ok, msg


def test_mate_in_1_wrong_move_rejected():
    puzzle = get_puzzle("m1-backrank-rook")
    ok, _ = verify_solution(puzzle, "h1g1")  # a legal but non-mating king move
    assert not ok


def test_mate_in_1_illegal_move_rejected():
    puzzle = get_puzzle("m1-backrank-rook")
    ok, msg = verify_solution(puzzle, "a1a4a")  # malformed / illegal
    assert not ok


def test_mate_in_2_key_move_verifies():
    puzzle = get_puzzle("m2-queen-confine-a")
    ok, msg = verify_solution(puzzle, puzzle["solution"][0])
    assert ok, msg


def test_mate_in_2_rejects_a_move_that_only_mates_in_more():
    puzzle = get_puzzle("m2-queen-confine-a")
    # A random legal king step should not force mate in two here.
    board = Board.from_fen(puzzle["fen"])
    legal = [m.uci() for m in board.legal_moves()]
    # Find a move that is NOT a forced mate-in-2 and confirm it is rejected.
    rejected_any = False
    for uci in legal:
        ok, _ = verify_solution(puzzle, uci)
        if not ok:
            rejected_any = True
            break
    assert rejected_any, "expected at least one non-solution move to be rejected"


def test_win_material_verifies_and_reports_gain():
    puzzle = get_puzzle("tac-hanging-queen")
    ok, msg = verify_solution(puzzle, "d1d6")
    assert ok, msg
    assert net_material_gain(Board.from_fen(puzzle["fen"]), "d1d6") >= 8.0


def test_win_material_rejects_non_winning_move():
    puzzle = get_puzzle("tac-hanging-queen")
    ok, _ = verify_solution(puzzle, "g1h1")  # a quiet king move wins nothing
    assert not ok


def test_verify_puzzle_full_bank_entries():
    for pid in ("m1-two-rooks", "m1-smothered", "m2-queen-confine-b"):
        ok, msg = verify_puzzle(get_puzzle(pid))
        assert ok, f"{pid}: {msg}"
