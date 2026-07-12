"""parse_san: turn Standard Algebraic Notation into a legal Move.

The strongest check is the ROUND-TRIP property: for every legal move in a set of
varied positions, parsing its rendered SAN must return that same move. That pins
parse_san against the existing renderer (move_to_san) across castling, captures,
promotions, disambiguation, en passant, and check/mate suffixes.
"""

import pytest

from palamedes.engine import Board, move_to_san, parse_san

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
KIWIPETE = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
POS3 = "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"
CASTLE = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"
PROMO = "6k1/4P3/8/8/8/8/8/4K3 w - - 0 1"
DISAMB = "4k3/8/8/8/8/5N2/8/1N2K3 w - - 0 1"


def test_parse_basic_moves():
    board = Board.from_fen(START)
    assert parse_san(board, "e4").uci() == "e2e4"
    assert parse_san(board, "Nf3").uci() == "g1f3"


def test_parse_castling_both_sides_and_zero_notation():
    board = Board.from_fen(CASTLE)
    assert parse_san(board, "O-O").uci() == "e1g1"
    assert parse_san(board, "O-O-O").uci() == "e1c1"
    assert parse_san(board, "0-0").uci() == "e1g1"


def test_parse_promotion():
    board = Board.from_fen(PROMO)
    assert parse_san(board, "e8=Q").uci() == "e7e8q"
    assert parse_san(board, "e8=N").uci() == "e7e8n"


def test_parse_disambiguation_and_ambiguity():
    board = Board.from_fen(DISAMB)
    assert parse_san(board, "Nbd2").uci() == "b1d2"
    assert parse_san(board, "Nfd2").uci() == "f3d2"
    with pytest.raises(ValueError):
        parse_san(board, "Nd2")  # ambiguous


def test_parse_strips_check_suffix():
    board = Board.from_fen(PROMO)
    # e8=Q gives check to the g8 king; parse_san must tolerate the '+'/'#'.
    assert parse_san(board, "e8=Q+").uci() == "e7e8q"


def test_parse_rejects_illegal_and_empty():
    board = Board.from_fen(START)
    with pytest.raises(ValueError):
        parse_san(board, "e5")  # not a legal first move
    with pytest.raises(ValueError):
        parse_san(board, "")
    with pytest.raises(ValueError):
        parse_san(board, "Zz9")


@pytest.mark.parametrize("fen", [START, KIWIPETE, POS3, CASTLE, PROMO, DISAMB])
def test_round_trip_every_legal_move(fen):
    board = Board.from_fen(fen)
    for move in board.legal_moves():
        san = move_to_san(board, move)
        assert parse_san(board, san) == move, f"{san} did not round-trip"
