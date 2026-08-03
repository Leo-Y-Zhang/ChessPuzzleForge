"""Hostile-input sweep: every public entry fails loud (ValueError) or degrades
safely - never an unhandled traceback or a silent wrong guess."""

import pytest

from chesspuzzleforge.difficulty import difficulty
from chesspuzzleforge.engine import Board, move_from_uci, parse_san
from chesspuzzleforge.export import puzzle_to_json, puzzle_to_pgn
from chesspuzzleforge.generator import generate_puzzle
from chesspuzzleforge.tactics import find_forks, find_pins, find_skewers

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


@pytest.mark.parametrize(
    "bad_fen",
    [
        "not a fen",
        "8/8/8/8/8/8/8 w - - 0 1",  # only 7 ranks
        "9/8/8/8/8/8/8/8 w - - 0 1",  # a rank summing to 9
        "xnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",  # bad piece 'x'
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR z KQkq - 0 1",  # bad side 'z'
    ],
)
def test_board_from_fen_rejects_bad_fen(bad_fen):
    with pytest.raises(ValueError):
        Board.from_fen(bad_fen)


def test_move_from_uci_rejects_malformed_and_illegal():
    board = Board.from_fen(START)
    with pytest.raises(ValueError):
        move_from_uci(board, "zz")  # malformed
    with pytest.raises(ValueError):
        move_from_uci(board, "e2e5")  # illegal pawn overreach


@pytest.mark.parametrize("bad", ["Zz9", "", "O-O-O-O"])
def test_parse_san_rejects_garbage(bad):
    with pytest.raises(ValueError):
        parse_san(Board.from_fen(START), bad)


def test_difficulty_rejects_unknown_goal():
    with pytest.raises(ValueError):
        difficulty({"fen": START, "goal": "bogus"})


def test_generate_puzzle_impossible_request_fails_loud():
    with pytest.raises(ValueError):
        generate_puzzle(goal="mate_in_3", difficulty="easy")


def test_export_rejects_a_malformed_puzzle():
    with pytest.raises(ValueError):
        puzzle_to_json({"goal": "mate_in_1"})  # no fen
    with pytest.raises(ValueError):
        puzzle_to_pgn({"fen": START, "goal": "mate_in_1"})  # no solution


def test_tactics_on_a_bare_king_board_return_empty():
    board = Board.from_fen("4k3/8/4K3/8/8/8/8/8 w - - 0 1")
    assert find_forks(board) == []
    assert find_pins(board) == []
    assert find_skewers(board) == []
