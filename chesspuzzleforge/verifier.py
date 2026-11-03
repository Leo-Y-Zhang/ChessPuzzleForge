"""Puzzle verification built on the self-contained :mod:`chesspuzzleforge.engine`.

The verifier confirms that a puzzle's stated solution really achieves its goal:

* ``mate_in_1`` / ``mate_in_2`` - the move forces checkmate within the stated
  number of the mover's moves, against *any* defence.
* ``win_material`` - the move nets at least ``threshold`` pawns of material
  against every legal reply, followed by the tactics module's capture search.

None of this depends on ``python-chess``; it is all pure standard library.
"""

from __future__ import annotations

from .engine import Board, Move, forced_mate_move, game_ending_refutation, move_from_uci
from .fen_bank import Puzzle
from .tactics import (
    _INFINITY,
    _SEARCH_NODE_BUDGET,
    _Budget,
    _BudgetExceeded,
    _capture_value,
    _forced_gain,
)

# Standard material values in pawns; the king is never captured so it is 0.
PIECE_VALUES = {"P": 1.0, "N": 3.0, "B": 3.0, "R": 5.0, "Q": 9.0, "K": 0.0}


def net_material_gain(board: Board, uci: str) -> float:
    """Material won after every legal reply and optimal capture play anywhere.

    Uses the same bounded search as fork detection. Returns negative infinity
    if the budget is exhausted, so an unproven gain cannot be accepted.
    """
    move = move_from_uci(board, uci)
    try:
        return _capture_value(board, move) - _forced_gain(
            board.push(move), 1, -_INFINITY, _INFINITY, _Budget(_SEARCH_NODE_BUDGET)
        )
    except _BudgetExceeded:
        return float("-inf")


def verify_solution(puzzle: Puzzle, uci: str) -> tuple[bool, str]:
    """Verify a *single* candidate first move against a puzzle's goal.

    Returns ``(ok, message)``.  ``ok`` is True when ``uci`` genuinely achieves
    the puzzle's goal from its FEN, regardless of whether it is the exact move
    listed in the bank (there can be more than one mating move).
    """
    board = Board.from_fen(puzzle["fen"])

    # The move must at least be legal in the position.
    try:
        move = move_from_uci(board, uci)
    except ValueError as exc:
        return False, f"illegal move: {exc}"

    goal = puzzle["goal"]
    if goal == "mate_in_1":
        child = board.push(move)
        if child.is_checkmate():
            return True, "delivers checkmate"
        return False, "does not deliver checkmate"

    if goal == "mate_in_2":
        child = board.push(move)
        if child.is_checkmate():
            return True, "delivers immediate checkmate"
        # For the candidate specifically, verify it forces mate in <= 2.
        if _move_forces_mate(board, move, 2):
            return True, "forces mate in two"
        # Only on failure search for *a* forcing move as a hint: the success
        # path stays cheap even on a full board (the exhaustive whole-position
        # search runs only to explain a wrong answer).
        found = forced_mate_move(board, 2)
        hint = f" (a forcing move is {found})" if found else ""
        return False, "does not force mate in two" + hint

    if goal == "mate_in_3":
        child = board.push(move)
        if child.is_checkmate():
            return True, "delivers immediate checkmate"
        if _move_forces_mate(board, move, 3):
            return True, "forces mate in three"
        found = forced_mate_move(board, 3)
        hint = f" (a forcing move is {found})" if found else ""
        return False, "does not force mate in three" + hint

    if goal == "win_material":
        # The capture search scores terminal positions as no material change;
        # first rule out a move that stalemates or walks into mate in one.
        refutation = game_ending_refutation(board.push(move))
        if refutation is not None:
            return False, refutation
        threshold = float(puzzle.get("threshold", 1.0))
        gain = net_material_gain(board, uci)
        if gain >= threshold:
            return True, f"wins {gain:g} pawns of material"
        return False, f"only wins {gain:g} pawns (need {threshold:g})"

    return False, f"unknown goal: {goal!r}"


def _move_forces_mate(board: Board, move: Move, depth: int) -> bool:
    """True if ``move`` (legal in ``board``) forces mate in at most ``depth``."""
    child = board.push(move)
    if child.is_checkmate():
        return True
    if depth <= 1:
        return False
    # Every opponent reply must still allow a forced mate in depth-1.
    replies = child.legal_moves()
    if not replies:
        return False  # stalemate, not mate
    for reply in replies:
        after = child.push(reply)
        if forced_mate_move(after, depth - 1) is None:
            return False
    return True


def verify_puzzle(puzzle: Puzzle) -> tuple[bool, str]:
    """Verify that *every* listed solution move achieves the puzzle's goal."""
    if not puzzle.get("solution"):
        return False, "puzzle has no solution moves"
    for uci in puzzle["solution"]:
        ok, message = verify_solution(puzzle, uci)
        if not ok:
            return False, f"{uci}: {message}"
    return True, "all listed solutions verified"
