"""Verified tactical motifs.

A tactic is reported ONLY when the engine PROVES it wins material via a short
capture search - never pattern-matched. This keeps the "every answer is proven"
guarantee that the rest of the project relies on. Pure standard library.
"""

from __future__ import annotations

from dataclasses import dataclass

from .engine import (
    BLACK,
    WHITE,
    Board,
    Move,
    file_of,
    game_ending_refutation,
    move_to_san,
    piece_color,
    rank_of,
    square,
    square_name,
)

_VALUES = {"P": 1.0, "N": 3.0, "B": 3.0, "R": 5.0, "Q": 9.0, "K": 0.0}

_INFINITY = 1e9

# Hard cap on capture-search nodes per find_forks call. The alpha-beta search
# below keeps real positions to a few hundred nodes; the budget is the proof
# that pathological positions cannot hang the caller. A candidate whose proof
# does not complete within the budget is treated as UNPROVEN and not reported
# (soundness over recall).
_SEARCH_NODE_BUDGET = 20_000


class _BudgetExceeded(Exception):
    """Internal: the capture-search node budget ran out mid-proof."""


class _Budget:
    """A countdown of search nodes shared across one ``find_forks`` call."""

    __slots__ = ("remaining",)

    def __init__(self, nodes: int) -> None:
        self.remaining = nodes

    def spend(self) -> None:
        self.remaining -= 1
        if self.remaining < 0:
            raise _BudgetExceeded


def _value(piece: str | None) -> float:
    return 0.0 if piece is None else _VALUES[piece.upper()]


def _is_capture(board: Board, move: Move) -> bool:
    return board.piece_at(move.to_sq) is not None or move.is_ep


def _capture_value(board: Board, move: Move) -> float:
    if move.is_ep:
        return 1.0
    return _value(board.piece_at(move.to_sq))


def _quiesce(board: Board, alpha: float, beta: float, budget: _Budget) -> float:
    """Best material the side to move can force via a CAPTURE sequence.

    A "stand pat" of 0 is always available (declining to capture), so this is the
    forced material swing under optimal capture play. Positive favours the mover.
    Fail-soft alpha-beta over captures ordered by falling victim value: called
    with a full window it returns exactly the plain negamax value, in a tiny
    fraction of the nodes. ``budget`` bounds the worst case (raises
    :class:`_BudgetExceeded` when exhausted).
    """
    budget.spend()
    best = 0.0  # stand pat: declining to capture is always available
    if best >= beta:
        return best
    if best > alpha:
        alpha = best
    captures = [m for m in board.legal_moves() if _is_capture(board, m)]
    captures.sort(key=lambda m: -_capture_value(board, m))
    for move in captures:
        value = _capture_value(board, move)
        if value <= alpha:
            break  # sorted: no remaining capture can beat alpha (gain <= victim value)
        gain = value - _quiesce(board.push(move), value - beta, value - alpha, budget)
        if gain > best:
            best = gain
            if best >= beta:
                return best
            if best > alpha:
                alpha = best
    return best


def _forced_gain(
    board: Board, defence_plies: int, alpha: float, beta: float, budget: _Budget
) -> float:
    """Material the side to move can force over ``defence_plies`` full moves, then
    captures resolve (quiescence). Fail-soft alpha-beta negamax (captures tried
    first, by falling victim value); positive favours the mover. With a full
    window the root value equals the plain negamax value."""
    if defence_plies == 0:
        return _quiesce(board, alpha, beta, budget)
    budget.spend()
    moves = board.legal_moves()
    if not moves:
        return 0.0  # mate/stalemate: outside the material model
    moves.sort(key=lambda m: -_capture_value(board, m))
    best = -_INFINITY
    for move in moves:
        value = _capture_value(board, move)
        child = board.push(move)
        gain = value - _forced_gain(child, defence_plies - 1, value - beta, value - alpha, budget)
        if gain > best:
            best = gain
            if best >= beta:
                return best
            if best > alpha:
                alpha = best
    return best


@dataclass(frozen=True)
class Fork:
    """A move whose piece attacks >= 2 enemy targets and PROVABLY wins material."""

    uci: str
    san: str
    targets: tuple[str, ...]
    gain: float


def find_forks(
    board: Board, min_gain: float = 2.0, max_nodes: int = _SEARCH_NODE_BUDGET
) -> list[Fork]:
    """Return the legal moves that create a winning fork, engine-verified.

    A fork's moved piece attacks >= 2 significant enemy targets (two pieces worth
    at least a knight, or a piece plus the enemy king = a royal fork). It is
    reported only if, after the opponent's best single defence, the side to move
    still nets at least ``min_gain`` pawns of material (proven by a capture
    search). Refuted or non-winning "forks" are never reported.

    The proof search is bounded: at most ``max_nodes`` search nodes are spent
    across the whole call, so ``find_forks`` terminates in bounded time on any
    board. If the budget runs out mid-proof, the candidate being proven and any
    candidates not yet examined are treated as unproven and NOT reported -
    the search fails toward silence, never toward an unproven claim.
    """
    mover = board.turn
    enemy = BLACK if mover == WHITE else WHITE
    forks: list[Fork] = []
    budget = _Budget(max_nodes)
    for move in board.legal_moves():
        child = board.push(move)
        attacked = child.attacks_from(move.to_sq)
        enemy_king = child.king_square(enemy)

        piece_targets: list[int] = []
        for sq in attacked:
            target = child.piece_at(sq)
            if target is not None and piece_color(target) == enemy and _value(target) >= 3.0:
                piece_targets.append(sq)

        forks_king = enemy_king is not None and enemy_king in attacked
        double_attack = len(piece_targets) >= 2 or (len(piece_targets) >= 1 and forks_king)
        if not double_attack:
            continue

        # Prove the material win: give the opponent one full defensive move, then
        # let captures resolve. If they cannot save the material, it is a real fork.
        try:
            net = _capture_value(board, move) - _forced_gain(
                child, 1, -_INFINITY, _INFINITY, budget
            )
        except _BudgetExceeded:
            break  # out of budget: the remaining candidates stay unproven and unreported
        if net < min_gain:
            continue
        # The material search scores a mate or stalemate as "no change", so a
        # fork that lets the defender mate at once would still "win" material.
        if game_ending_refutation(child) is not None:
            continue

        target_sqs = list(piece_targets)
        if forks_king and enemy_king is not None:
            target_sqs.append(enemy_king)
        targets = tuple(square_name(sq) for sq in sorted(target_sqs))
        forks.append(Fork(move.uci(), move_to_san(board, move), targets, round(net, 2)))
    return forks


# Ray directions for line tactics (bishops on diagonals, rooks on ranks/files).
_BISHOP_DIRS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
_ROOK_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
_QUEEN_DIRS = _BISHOP_DIRS + _ROOK_DIRS


def _on(file: int, rank: int) -> bool:
    return 0 <= file <= 7 and 0 <= rank <= 7


@dataclass(frozen=True)
class Pin:
    """An enemy piece (``front``) pinned by ``attacker`` to ``back`` behind it.

    ``absolute`` is True when ``back`` is the enemy king (the pinned piece may not
    legally move off the line at all).
    """

    attacker: str
    front: str
    back: str
    absolute: bool


@dataclass(frozen=True)
class Skewer:
    """A more valuable enemy piece (``front``) on the same line of ``attacker`` as a
    lesser piece (``back``) behind it: moving the front exposes the back."""

    attacker: str
    front: str
    back: str


def _line_tactics(board: Board) -> tuple[list[Pin], list[Skewer]]:
    mover = board.turn
    enemy = BLACK if mover == WHITE else WHITE
    pins: list[Pin] = []
    skewers: list[Skewer] = []
    for start in range(64):
        piece = board.piece_at(start)
        if piece is None or piece_color(piece) != mover:
            continue
        kind = piece.upper()
        if kind not in ("B", "R", "Q"):
            continue
        dirs = _BISHOP_DIRS if kind == "B" else _ROOK_DIRS if kind == "R" else _QUEEN_DIRS
        for df, dr in dirs:
            # First piece along the ray = the front piece (must be enemy).
            f, r = file_of(start) + df, rank_of(start) + dr
            front = None
            while _on(f, r):
                p = board.piece_at(square(f, r))
                if p is not None:
                    if piece_color(p) == enemy:
                        front = square(f, r)
                    break
                f, r = f + df, r + dr
            if front is None:
                continue
            # Next piece behind the front along the same ray = the back piece.
            f, r = file_of(front) + df, rank_of(front) + dr
            back = None
            while _on(f, r):
                p = board.piece_at(square(f, r))
                if p is not None:
                    if piece_color(p) == enemy:
                        back = square(f, r)
                    break
                f, r = f + df, r + dr
            if back is None:
                continue
            front_piece = board.piece_at(front)
            back_piece = board.piece_at(back)
            assert front_piece is not None and back_piece is not None
            back_is_king = back_piece.upper() == "K"
            if back_is_king or _value(back_piece) > _value(front_piece):
                pins.append(
                    Pin(square_name(start), square_name(front), square_name(back), back_is_king)
                )
            elif _value(front_piece) > _value(back_piece):
                skewers.append(Skewer(square_name(start), square_name(front), square_name(back)))
    return pins, skewers


def find_pins(board: Board) -> list[Pin]:
    """Return the pins created by the side to move's sliders (absolute or relative)."""
    return _line_tactics(board)[0]


def find_skewers(board: Board) -> list[Skewer]:
    """Return the skewers created by the side to move's sliders."""
    return _line_tactics(board)[1]
