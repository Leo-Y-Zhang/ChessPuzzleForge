"""Perft: pin the engine's legal move generation against KNOWN reference counts.

Perft (performance test) counts the leaf nodes of the legal-move tree to a given
depth. These reference values are standard and independently published; matching
them across positions that exercise castling, en passant, promotions, checks and
pins is a strong correctness pin for the move generator - the foundation of the
"every answer is proven" guarantee.
"""

import pytest

from chesspuzzleforge.engine import Board, perft

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
KIWIPETE = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
POS3 = "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"
POS4 = "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1"
POS4_MIRRORED = "r2q1rk1/pP1p2pp/Q4n2/bbp1p3/Np6/1B3NBn/pPPP1PPP/R3K2R b KQ - 0 1"
POS5 = "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8"
POS6 = "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10"

CASES = [
    (START, 1, 20),
    (START, 2, 400),
    (START, 3, 8902),
    (KIWIPETE, 1, 48),
    (KIWIPETE, 2, 2039),
    (KIWIPETE, 3, 97862),
    (POS3, 1, 14),
    (POS3, 2, 191),
    (POS3, 3, 2812),
    (POS3, 4, 43238),
    (POS4, 1, 6),
    (POS4, 2, 264),
    (POS4, 3, 9467),
    # The same position with colours swapped must give the same counts: this
    # catches any asymmetry between the White and Black move generators.
    (POS4_MIRRORED, 1, 6),
    (POS4_MIRRORED, 2, 264),
    (POS4_MIRRORED, 3, 9467),
    (POS5, 1, 44),
    (POS5, 2, 1486),
    (POS5, 3, 62379),
    (POS6, 1, 46),
    (POS6, 2, 2079),
    (POS6, 3, 89890),
]


@pytest.mark.parametrize("fen,depth,expected", CASES)
def test_perft_matches_reference(fen, depth, expected):
    assert perft(Board.from_fen(fen), depth) == expected


def test_perft_depth_zero_is_one():
    assert perft(Board.from_fen(START), 0) == 1


def test_perft_rejects_negative_depth():
    with pytest.raises(ValueError):
        perft(Board.from_fen(START), -1)
