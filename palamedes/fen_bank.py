"""A curated, self-contained bank of chess puzzles.

Every entry is a plain dict so the bank has zero third-party dependencies and
can be loaded and tested with only the Python standard library.  Each puzzle's
correctness is asserted by the project's tests using the pure-Python engine in
:mod:`palamedes.engine`, so the answers below are verified, not assumed.

Puzzle schema
-------------
* ``id``          - stable string identifier.
* ``fen``         - the position (Forsyth-Edwards Notation).
* ``goal``        - one of ``mate_in_1``, ``mate_in_2``, ``win_material``.
* ``solution``    - list of accepted first moves in UCI notation.  For a mate
                    puzzle any listed move forces the mate; usually there is a
                    single unique key move.
* ``san``         - human-readable description of the key move (for display).
* ``threshold``   - (win_material only) minimum material to win, in pawns.
* ``theme``       - short human label for the tactic/mate motif.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict


class Puzzle(TypedDict):
    """Schema for a bank puzzle (``threshold`` only on win-material puzzles)."""

    id: str
    fen: str
    goal: str
    solution: list[str]
    san: str
    theme: str
    threshold: NotRequired[float]


PUZZLES: list[Puzzle] = [
    # ---------------------------------------------------------- mate in one
    {
        "id": "m1-backrank-rook",
        "fen": "6k1/5ppp/8/8/8/8/8/R6K w - - 0 1",
        "goal": "mate_in_1",
        "solution": ["a1a8"],
        "san": "Ra8#",
        "theme": "back-rank mate",
    },
    {
        "id": "m1-backrank-queen",
        "fen": "6k1/5ppp/8/8/8/8/5PPP/3Q2K1 w - - 0 1",
        "goal": "mate_in_1",
        "solution": ["d1d8"],
        "san": "Qd8#",
        "theme": "back-rank mate",
    },
    {
        "id": "m1-two-rooks",
        "fen": "7k/R7/1R6/8/8/8/8/7K w - - 0 1",
        "goal": "mate_in_1",
        "solution": ["b6b8"],
        "san": "Rb8#",
        "theme": "two-rook mate",
    },
    {
        "id": "m1-rook-escort",
        "fen": "6k1/4Rppp/8/8/8/8/5PPP/6K1 w - - 0 1",
        "goal": "mate_in_1",
        "solution": ["e7e8"],
        "san": "Re8#",
        "theme": "back-rank mate",
    },
    {
        "id": "m1-queen-escort",
        "fen": "6k1/8/6K1/8/8/8/8/3Q4 w - - 0 1",
        "goal": "mate_in_1",
        "solution": ["d1d8"],
        "san": "Qd8#",
        "theme": "queen-and-king mate",
    },
    {
        "id": "m1-smothered",
        "fen": "6rk/6pp/8/6N1/8/8/8/6K1 w - - 0 1",
        "goal": "mate_in_1",
        "solution": ["g5f7"],
        "san": "Nf7#",
        "theme": "smothered mate",
    },
    # ---------------------------------------------------------- mate in two
    {
        "id": "m2-queen-confine-a",
        "fen": "8/8/8/8/8/8/k7/2K2Q2 w - - 0 1",
        "goal": "mate_in_2",
        "solution": ["f1h3"],
        "san": "Qh3 (then mate next move)",
        "theme": "queen confinement, mate in two",
    },
    {
        "id": "m2-queen-confine-b",
        "fen": "8/8/8/8/8/3Q4/k7/2K5 w - - 0 1",
        "goal": "mate_in_2",
        "solution": ["d3h3"],
        "san": "Qh3 (then mate next move)",
        "theme": "queen confinement, mate in two",
    },
    # ------------------------------------------------------------- tactics
    {
        "id": "tac-hanging-queen",
        "fen": "6k1/5ppp/3q4/8/8/8/5PPP/3R2K1 w - - 0 1",
        "goal": "win_material",
        "solution": ["d1d6"],
        "san": "Rxd6",
        "threshold": 8.0,
        "theme": "winning an undefended queen",
    },
]


def all_puzzles() -> list[Puzzle]:
    """Return a shallow copy of the puzzle bank."""
    return [p.copy() for p in PUZZLES]


def puzzles_by_goal(goal: str) -> list[Puzzle]:
    """Return the puzzles whose ``goal`` matches ``goal``."""
    return [p.copy() for p in PUZZLES if p["goal"] == goal]


def get_puzzle(puzzle_id: str) -> Puzzle:
    """Return the puzzle with the given id, or raise ``KeyError``."""
    for p in PUZZLES:
        if p["id"] == puzzle_id:
            return p.copy()
    raise KeyError(puzzle_id)
