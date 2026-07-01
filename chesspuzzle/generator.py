"""Puzzle generation and presentation.

The generator does two complementary things:

1. **Derivation** - given *any* position it can discover the mate-in-1 (or
   mate-in-2) moves from first principles using the engine's search.  This is
   how the tool "generates" a puzzle from a raw position rather than trusting a
   hand-written answer.
2. **Curation** - it can also draw a validated puzzle from the built-in bank
   (:mod:`chesspuzzle.fen_bank`), which is the reliable fallback when no
   position source is supplied.

Everything here is pure standard library.
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional

from .engine import Board, forced_mate_move
from .fen_bank import all_puzzles, puzzles_by_goal
from .verifier import verify_puzzle


def derive_mate_in_1(fen: str) -> List[str]:
    """Return every move (UCI) that delivers immediate checkmate in ``fen``."""
    board = Board.from_fen(fen)
    mates = []
    for move in board.legal_moves():
        if board.push(move).is_checkmate():
            mates.append(move.uci())
    return mates


def derive_mate_in_2(fen: str) -> Optional[str]:
    """Return one move that forces mate in two (or fewer), or None."""
    return forced_mate_move(Board.from_fen(fen), 2)


def make_puzzle_from_position(fen: str, puzzle_id: str = "derived") -> Optional[Dict]:
    """Build a mate-in-1 puzzle by deriving the solution from a raw position.

    Returns None if the position has no mate in one.
    """
    mates = derive_mate_in_1(fen)
    if not mates:
        return None
    return {
        "id": puzzle_id,
        "fen": fen,
        "goal": "mate_in_1",
        "solution": mates,
        "san": mates[0],
        "theme": "derived mate-in-one",
    }


def generate_puzzle(
    goal: Optional[str] = None,
    seed: Optional[int] = None,
    validate: bool = True,
) -> Dict:
    """Return a random, verified puzzle from the bank.

    ``goal`` optionally filters by ``mate_in_1`` / ``mate_in_2`` /
    ``win_material``.  When ``validate`` is True (the default) the chosen puzzle
    is re-verified with the engine before being returned, so a caller can trust
    the answer is correct.
    """
    rng = random.Random(seed)
    pool = puzzles_by_goal(goal) if goal else all_puzzles()
    if not pool:
        raise ValueError(f"no puzzles available for goal {goal!r}")
    puzzle = rng.choice(pool)
    if validate:
        ok, message = verify_puzzle(puzzle)
        if not ok:
            raise AssertionError(f"bank puzzle {puzzle['id']} failed verification: {message}")
    return puzzle


def render_puzzle(puzzle: Dict, reveal: bool = False) -> str:
    """Return a human-readable, printable rendering of a puzzle."""
    board = Board.from_fen(puzzle["fen"])
    side = "White" if board.turn == "w" else "Black"
    goal_labels = {
        "mate_in_1": "Mate in 1",
        "mate_in_2": "Mate in 2",
        "win_material": "Win material",
    }
    goal = goal_labels.get(puzzle["goal"], puzzle["goal"])

    lines = [
        f"Puzzle: {puzzle['id']}",
        f"Theme:  {puzzle.get('theme', '-')}",
        f"Goal:   {goal}  ({side} to move)",
        "",
        board.ascii(perspective=board.turn),
        "",
        f"FEN: {puzzle['fen']}",
    ]
    if reveal:
        lines.append("")
        lines.append(f"Solution: {puzzle.get('san', puzzle['solution'][0])}  "
                     f"(UCI: {', '.join(puzzle['solution'])})")
    return "\n".join(lines)
