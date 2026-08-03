"""Bank tests - pure standard library.  These MUST always run green."""

from __future__ import annotations

import pytest

from chesspuzzleforge.engine import Board
from chesspuzzleforge.fen_bank import PUZZLES, all_puzzles, get_puzzle, puzzles_by_goal
from chesspuzzleforge.verifier import verify_puzzle


def test_bank_is_non_empty_and_has_each_goal():
    goals = {p["goal"] for p in PUZZLES}
    assert {"mate_in_1", "mate_in_2", "win_material"} <= goals


def test_puzzle_ids_are_unique():
    ids = [p["id"] for p in PUZZLES]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("puzzle", PUZZLES, ids=[p["id"] for p in PUZZLES])
def test_every_bank_puzzle_verifies(puzzle):
    ok, message = verify_puzzle(puzzle)
    assert ok, f"{puzzle['id']} failed: {message}"


@pytest.mark.parametrize("puzzle", PUZZLES, ids=[p["id"] for p in PUZZLES])
def test_every_fen_parses_and_side_to_move_is_valid(puzzle):
    board = Board.from_fen(puzzle["fen"])
    assert board.turn in ("w", "b")
    # The side to move must have the king it is about to (help)mate with present.
    assert board.king_square("w") is not None
    assert board.king_square("b") is not None


def test_get_puzzle_and_filters():
    assert get_puzzle("m1-backrank-rook")["goal"] == "mate_in_1"
    assert all(p["goal"] == "mate_in_1" for p in puzzles_by_goal("mate_in_1"))
    with pytest.raises(KeyError):
        get_puzzle("does-not-exist")


def test_all_puzzles_returns_copies():
    a = all_puzzles()
    a[0]["id"] = "mutated"
    assert PUZZLES[0]["id"] != "mutated"
