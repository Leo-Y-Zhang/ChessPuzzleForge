"""Deterministic JSON and PGN export."""

import json

import pytest

from chesspuzzleforge.export import puzzle_to_json, puzzle_to_pgn
from chesspuzzleforge.fen_bank import get_puzzle

BACKRANK = get_puzzle("m1-backrank-rook")


def test_json_is_deterministic_and_sorted():
    a = puzzle_to_json(BACKRANK)
    assert a == puzzle_to_json(BACKRANK)  # deterministic
    assert json.loads(a)["fen"] == BACKRANK["fen"]
    assert a.index('"fen"') < a.index('"goal"') < a.index('"id"')  # sorted keys


def test_pgn_carries_fen_setup_and_key_move_without_a_real_date():
    pgn = puzzle_to_pgn(BACKRANK)
    assert '[FEN "6k1/5ppp/8/8/8/8/8/R6K w - - 0 1"]' in pgn
    assert '[SetUp "1"]' in pgn
    assert "Ra8#" in pgn
    assert '[Date "????.??.??"]' in pgn  # deterministic placeholder, never today


def test_export_fails_loud_on_a_bad_puzzle():
    with pytest.raises(ValueError):
        puzzle_to_json({"goal": "mate_in_1"})  # no fen
    # A puzzle with no solution list cannot be exported to PGN.
    with pytest.raises(ValueError):
        puzzle_to_pgn({"fen": "6k1/5ppp/8/8/8/8/8/R6K w - - 0 1", "goal": "mate_in_1"})
