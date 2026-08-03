"""Generator + rendering tests - pure standard library."""

from __future__ import annotations

import pytest

from chesspuzzleforge.generator import (
    derive_mate_in_1,
    derive_mate_in_2,
    generate_puzzle,
    make_puzzle_from_position,
    render_puzzle,
)
from chesspuzzleforge.verifier import verify_puzzle


def test_derive_mate_in_1_finds_the_backrank_mate():
    mates = derive_mate_in_1("6k1/5ppp/8/8/8/8/8/R6K w - - 0 1")
    assert mates == ["a1a8"]


def test_derive_mate_in_1_returns_empty_when_none():
    # Standard start position has no mate in one.
    assert derive_mate_in_1("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1") == []


def test_derive_mate_in_2_finds_forcing_move():
    move = derive_mate_in_2("8/8/8/8/8/8/k7/2K2Q2 w - - 0 1")
    assert move is not None


def test_make_puzzle_from_position_builds_verified_puzzle():
    puzzle = make_puzzle_from_position("6k1/5ppp/8/8/8/8/8/R6K w - - 0 1")
    assert puzzle is not None
    assert puzzle["goal"] == "mate_in_1"
    ok, msg = verify_puzzle(puzzle)
    assert ok, msg


def test_make_puzzle_from_position_none_when_no_mate():
    assert make_puzzle_from_position("8/8/8/8/8/8/8/k6K w - - 0 1") is None


def test_derived_puzzle_renders_san_with_mate_marker():
    # Regression: the derived mate-in-1 must display SAN (Ra8#), like the bank
    # puzzles, rather than the raw UCI (a1a8).
    puzzle = make_puzzle_from_position("6k1/5ppp/8/8/8/8/8/R6K w - - 0 1")
    assert puzzle is not None
    assert puzzle["san"] == "Ra8#"
    shown = render_puzzle(puzzle, reveal=True)
    assert "Solution: Ra8#" in shown
    assert "#" in shown  # the mate marker is present
    assert "a1a8" in shown  # UCI is still shown as a helpful cross-reference


def test_make_puzzle_from_position_rejects_invalid_fen():
    with pytest.raises(ValueError):
        make_puzzle_from_position("this is not a fen")


def test_generate_puzzle_is_validated():
    puzzle = generate_puzzle(seed=1)
    ok, msg = verify_puzzle(puzzle)
    assert ok, msg


def test_generate_puzzle_respects_goal():
    for _ in range(5):
        p = generate_puzzle(goal="mate_in_1", seed=None)
        assert p["goal"] == "mate_in_1"


def test_generate_puzzle_is_deterministic_with_seed():
    a = generate_puzzle(seed=42)
    b = generate_puzzle(seed=42)
    assert a["id"] == b["id"]


def test_generate_puzzle_unknown_goal_raises():
    with pytest.raises(ValueError):
        generate_puzzle(goal="mate_in_9")


def test_render_puzzle_labels_mate_in_3():
    # Regression: mate_in_3 was missing from the goal labels, so the raw string
    # "mate_in_3" leaked into the rendering instead of "Mate in 3".
    puzzle = generate_puzzle(goal="mate_in_3", seed=1)
    shown = render_puzzle(puzzle)
    assert "Mate in 3" in shown
    assert "mate_in_3" not in shown


def test_render_puzzle_hides_and_reveals_solution():
    puzzle = generate_puzzle(goal="mate_in_1", seed=3)
    hidden = render_puzzle(puzzle, reveal=False)
    shown = render_puzzle(puzzle, reveal=True)
    assert "FEN:" in hidden
    assert "Solution:" not in hidden
    assert "Solution:" in shown
    assert puzzle["solution"][0] in shown
