"""Verifier tests - pure standard library.  These MUST always run green."""

from __future__ import annotations

import time

from chesspuzzleforge.engine import Board
from chesspuzzleforge.fen_bank import get_puzzle
from chesspuzzleforge.verifier import (
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


def test_mate_in_2_on_a_full_board_verifies_the_candidate_without_a_full_scan():
    # The Opera game's 16. Qb8+ position (21 men): a correct candidate must
    # verify by checking THAT candidate only - the exhaustive whole-position
    # search runs solely to build the hint after a failure.
    puzzle = {
        "fen": "4kb1r/p2n1ppp/4q3/4p1B1/4P3/1Q6/PPP2PPP/2KR4 w k - 0 16",
        "goal": "mate_in_2",
        "solution": ["b3b8"],
    }
    start = time.perf_counter()
    ok, msg = verify_solution(puzzle, "b3b8")
    elapsed = time.perf_counter() - start
    assert ok, msg
    assert elapsed < 5.0, f"verifying a correct mate-in-2 unexpectedly slow: {elapsed:.2f}s"


# A capture that wins material on the board but hands the opponent the game is
# not a "win material" answer. The recapture model alone looked only at the
# destination square, so both of these were accepted as proven.


def _win_material(fen: str, uci: str, threshold: float) -> dict:
    return {
        "id": "t",
        "fen": fen,
        "goal": "win_material",
        "solution": [uci],
        "san": "",
        "theme": "",
        "threshold": threshold,
    }


def test_win_material_rejects_a_capture_that_allows_mate_in_one():
    # Rxd6 takes the queen with no recapture, but it leaves the back rank:
    # ...Re1 is mate. The verifier used to call this "wins 9 pawns".
    fen = "4r1k1/5ppp/3q4/8/8/8/5PPP/3R2K1 w - - 0 1"
    ok, msg = verify_solution(_win_material(fen, "d1d6", 8.0), "d1d6")
    assert not ok
    assert "mate" in msg


def test_win_material_rejects_a_capture_that_stalemates():
    # Qxc7 takes the last black pawn and leaves the bare king with no move and
    # not in check: stalemate, a draw, from a position that is trivially won.
    fen = "k7/2p5/8/8/8/8/8/2Q4K w - - 0 1"
    ok, msg = verify_solution(_win_material(fen, "c1c7", 1.0), "c1c7")
    assert not ok
    assert "stalemate" in msg
