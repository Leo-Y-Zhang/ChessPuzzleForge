"""Chess Puzzle Generator - a small, offline, pure-Python puzzle toolkit.

Public API re-exports for convenience::

    from palamedes import Board, generate_puzzle, verify_puzzle
"""

from __future__ import annotations

from .engine import Board, Move, forced_mate_move, move_from_uci, move_to_san, perft
from .fen_bank import all_puzzles, get_puzzle, puzzles_by_goal
from .generator import derive_mate_in_1, generate_puzzle, render_puzzle
from .verifier import net_material_gain, verify_puzzle, verify_solution

__all__ = [
    "Board",
    "Move",
    "forced_mate_move",
    "perft",
    "move_from_uci",
    "move_to_san",
    "all_puzzles",
    "get_puzzle",
    "puzzles_by_goal",
    "derive_mate_in_1",
    "generate_puzzle",
    "render_puzzle",
    "net_material_gain",
    "verify_puzzle",
    "verify_solution",
]

__version__ = "1.0.0"
