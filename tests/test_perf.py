"""Perf sanity: perft stays fast enough that an accidental blow-up is caught.

The timing lives only in this test; nothing time-based enters any output (the
engine and reports stay deterministic).
"""

import time

from chesspuzzleforge.engine import Board, perft

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def test_perft_startpos_depth3_is_correct_and_fast():
    board = Board.from_fen(START)
    start = time.perf_counter()
    nodes = perft(board, 3)
    elapsed = time.perf_counter() - start
    assert nodes == 8902
    assert elapsed < 10.0, f"perft(3) unexpectedly slow: {elapsed:.2f}s"
