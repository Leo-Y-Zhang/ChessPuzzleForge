"""Baseline invariants: engine sanity (perft), determinism, and import purity.

These pin the hard gate at the tooling level: the move generator agrees with
known reference perft counts, generation is reproducible by seed, and importing
the shipped package never drags in the optional ``python-chess`` referee.
"""

import subprocess
import sys

from chesspuzzleforge.engine import Board
from chesspuzzleforge.generator import generate_puzzle

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
KIWIPETE_FEN = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"


def _perft(board: Board, depth: int) -> int:
    if depth == 0:
        return 1
    return sum(_perft(board.push(m), depth - 1) for m in board.legal_moves())


def test_startpos_perft_1_is_20():
    assert _perft(Board.from_fen(START_FEN), 1) == 20


def test_kiwipete_perft_1_is_48():
    assert _perft(Board.from_fen(KIWIPETE_FEN), 1) == 48


def test_generate_puzzle_is_deterministic_by_seed():
    assert generate_puzzle(seed=5) == generate_puzzle(seed=5)


def test_import_chesspuzzleforge_does_not_need_chess():
    # The shipped core must import with zero third-party dependencies.
    code = "import sys, chesspuzzleforge; assert 'chess' not in sys.modules"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
