"""Chess Puzzle Generator - a small, offline, pure-Python puzzle toolkit.

Public API re-exports for convenience::

    from chesspuzzleforge import Board, generate_puzzle, verify_puzzle
"""

from __future__ import annotations

from .difficulty import difficulty
from .engine import (
    Board,
    Move,
    forced_mate_move,
    move_from_uci,
    move_to_san,
    parse_san,
    perft,
)
from .export import puzzle_to_json, puzzle_to_pgn
from .fen_bank import all_puzzles, get_puzzle, puzzles_by_goal
from .generator import derive_mate_in_1, generate_puzzle, render_puzzle
from .miner import mine_games, mine_pgn
from .pgn import PgnError, PgnGame, read_games
from .synth import parse_piece_set, synthesize_puzzle, synthesize_puzzles
from .tactics import Fork, Pin, Skewer, find_forks, find_pins, find_skewers
from .verifier import net_material_gain, verify_puzzle, verify_solution

__all__ = [
    "Board",
    "Move",
    "forced_mate_move",
    "perft",
    "move_from_uci",
    "move_to_san",
    "parse_san",
    "all_puzzles",
    "get_puzzle",
    "puzzles_by_goal",
    "derive_mate_in_1",
    "generate_puzzle",
    "render_puzzle",
    "difficulty",
    "puzzle_to_json",
    "puzzle_to_pgn",
    "PgnError",
    "PgnGame",
    "read_games",
    "mine_games",
    "mine_pgn",
    "parse_piece_set",
    "synthesize_puzzle",
    "synthesize_puzzles",
    "Fork",
    "find_forks",
    "Pin",
    "Skewer",
    "find_pins",
    "find_skewers",
    "net_material_gain",
    "verify_puzzle",
    "verify_solution",
]

__version__ = "2.2.0"  # kept in lockstep with pyproject [project] version
