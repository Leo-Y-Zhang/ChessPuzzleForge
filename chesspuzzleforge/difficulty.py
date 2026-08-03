"""Deterministic puzzle difficulty scoring.

Pure and reproducible - no wall-clock, no randomness. The score depends only on
the puzzle's goal, the branching at its key position, and how few first moves are
listed as solving it, so the same puzzle always scores identically.

Formula (documented so it is auditable):

    score = 8 * depth + 0.4 * branching + 0.3 * rarity

* ``depth``     - forcing length: mate_in_N -> N, win_material -> 1. The dominant
                  term, so deeper mates are harder.
* ``branching`` - number of legal moves at the key position (more choices to sift).
* ``rarity``    - branching minus the number of listed solving moves (more decoys
                  around the key move is harder).

Bands are fixed thresholds; see ``_EASY_MAX`` / ``_MEDIUM_MAX``.
"""

from __future__ import annotations

from collections.abc import Mapping

from .engine import Board

_DEPTH = {"mate_in_1": 1, "mate_in_2": 2, "mate_in_3": 3, "win_material": 1}
_EASY_MAX = 22.0
_MEDIUM_MAX = 30.0


def difficulty(puzzle: Mapping[str, object]) -> dict[str, object]:
    """Score a puzzle's difficulty deterministically.

    Returns ``{"score", "band", "factors"}``. Raises ``ValueError`` on a puzzle
    without a string ``fen``/``goal`` or with an unknown goal (never guesses).
    """
    goal = puzzle.get("goal")
    fen = puzzle.get("fen")
    if not isinstance(goal, str) or not isinstance(fen, str):
        raise ValueError("puzzle must have a string 'fen' and 'goal'")
    depth = _DEPTH.get(goal)
    if depth is None:
        raise ValueError(f"unknown goal for difficulty: {goal!r}")

    branching = len(Board.from_fen(fen).legal_moves())
    solution = puzzle.get("solution")
    solving = max(1, len(solution) if isinstance(solution, list) else 1)
    rarity = max(0, branching - solving)

    score = round(8.0 * depth + 0.4 * branching + 0.3 * rarity, 1)
    band = "easy" if score < _EASY_MAX else "medium" if score < _MEDIUM_MAX else "hard"
    return {
        "score": score,
        "band": band,
        "factors": {"depth": depth, "branching": branching, "solving": solving, "rarity": rarity},
    }
