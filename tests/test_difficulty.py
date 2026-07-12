"""Deterministic difficulty scoring + the --difficulty generation filter."""

import pytest

from palamedes.difficulty import difficulty
from palamedes.fen_bank import get_puzzle
from palamedes.generator import generate_puzzle


def test_deeper_mate_scores_harder():
    m1 = difficulty(get_puzzle("m1-smothered"))["score"]
    m2 = difficulty(get_puzzle("m2-queen-confine-a"))["score"]
    m3 = difficulty(get_puzzle("m3-two-rook-ladder"))["score"]
    assert m1 < m2 < m3


def test_scoring_is_deterministic():
    puzzle = get_puzzle("m3-two-rook-ladder")
    assert difficulty(puzzle) == difficulty(puzzle)


def test_band_is_valid_and_present_for_each_level():
    bands = {difficulty(p)["band"] for p in map(get_puzzle, [
        "m1-smothered", "m1-backrank-rook", "m2-queen-confine-a", "m3-two-rook-ladder",
    ])}
    assert bands <= {"easy", "medium", "hard"}
    assert "hard" in bands


def test_fails_loud_on_bad_puzzle():
    with pytest.raises(ValueError):
        difficulty({"fen": 123, "goal": "mate_in_1"})  # fen not a string
    with pytest.raises(ValueError):
        difficulty({"fen": "8/8/8/8/8/8/8/K6k w - - 0 1", "goal": "bogus"})


def test_generate_puzzle_difficulty_filter_returns_that_band():
    puzzle = generate_puzzle(difficulty="hard", seed=0)
    assert difficulty(puzzle)["band"] == "hard"


def test_generate_puzzle_impossible_filter_fails_loud():
    with pytest.raises(ValueError):
        generate_puzzle(goal="mate_in_3", difficulty="easy")  # the only mate_in_3 is hard
