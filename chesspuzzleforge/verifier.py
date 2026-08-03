"""Puzzle verification built on the self-contained :mod:`chesspuzzleforge.engine`.

The verifier confirms that a puzzle's stated solution really achieves its goal:

* ``mate_in_1`` / ``mate_in_2`` - the move forces checkmate within the stated
  number of the mover's moves, against *any* defence.
* ``win_material`` - the move is a capture that nets at least ``threshold``
  pawns of material even after the opponent's best recapture on that square.

None of this depends on ``python-chess``; it is all pure standard library.
"""

from __future__ import annotations

from .engine import Board, Move, forced_mate_move, move_from_uci
from .fen_bank import Puzzle

# Standard material values in pawns; the king is never captured so it is 0.
PIECE_VALUES = {"P": 1.0, "N": 3.0, "B": 3.0, "R": 5.0, "Q": 9.0, "K": 0.0}


def _value(piece: str | None) -> float:
    if piece is None:
        return 0.0
    return PIECE_VALUES[piece.upper()]


def net_material_gain(board: Board, uci: str) -> float:
    """Material (in pawns) won by playing ``uci``, after the best recapture.

    A capture wins ``value(captured)`` immediately; if the opponent can then
    recapture on the destination square, we subtract the value of the piece we
    left there (they will choose the recapture that costs us the most, which for
    a single square is simply the piece sitting on it).  En-passant captures are
    handled correctly because the pushed board removes the captured pawn.
    """
    move = move_from_uci(board, uci)
    captured_value = _value(board.piece_at(move.to_sq))
    if move.is_ep:
        captured_value = 1.0  # an en-passant capture always takes a pawn

    after = board.push(move)
    our_piece_value = _value(after.piece_at(move.to_sq))

    # Can the opponent recapture on the destination square?
    opponent_can_recapture = False
    for reply in after.legal_moves():
        if reply.to_sq == move.to_sq:
            opponent_can_recapture = True
            break

    if opponent_can_recapture:
        return captured_value - our_piece_value
    return captured_value


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
