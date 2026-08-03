"""Deterministic export of puzzles to portable formats (JSON and PGN).

Both renderings are deterministic - no wall-clock, no randomness - so identical
puzzles export identically. Pure standard library.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from .engine import Board, move_from_uci, move_to_san


def _require_str(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"puzzle {name} must be a string")
    return value


def puzzle_to_json(puzzle: Mapping[str, object]) -> str:
    """Deterministic JSON for a puzzle (keys sorted). Fails loud on a bad puzzle."""
    _require_str(puzzle.get("fen"), "fen")
    _require_str(puzzle.get("goal"), "goal")
    return json.dumps(dict(puzzle), sort_keys=True, ensure_ascii=False)


def puzzle_to_pgn(puzzle: Mapping[str, object]) -> str:
    """A minimal, valid PGN for a puzzle: the position plus its key move in SAN.

    Deterministic: the ``Date`` is the PGN "unknown" placeholder, never today's
    date, and the move is the first solution move rendered from the position.
    """
    fen = _require_str(puzzle.get("fen"), "fen")
    goal = _require_str(puzzle.get("goal"), "goal")
    solution = puzzle.get("solution")
    if not isinstance(solution, list) or not solution or not isinstance(solution[0], str):
        raise ValueError("puzzle must have a non-empty 'solution' list of UCI strings")

    board = Board.from_fen(fen)
    move = move_from_uci(board, solution[0])  # validates legality (fail-loud)
    san = move_to_san(board, move)
    move_text = f"{board.fullmove}. {san}" if board.turn == "w" else f"{board.fullmove}... {san}"

    tags = [
        '[Event "ChessPuzzleForge puzzle"]',
        '[Site "?"]',
        '[Date "????.??.??"]',
        '[Round "?"]',
        '[White "?"]',
        '[Black "?"]',
        '[Result "*"]',
        '[SetUp "1"]',
        f'[FEN "{fen}"]',
        f'[PuzzleGoal "{goal}"]',
    ]
    return "\n".join(tags) + "\n\n" + move_text + " *\n"
