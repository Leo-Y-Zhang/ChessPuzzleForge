"""Seeded synthesis of fresh, engine-verified mate-in-N endgame puzzles.

The synthesizer samples positions uniformly from a bounded piece set - the
white king, one to three white pieces drawn from Q/R/B/N, and the bare black
king, White to move - using ``random.Random(seed)``, so the same seed and
parameters always yield the same puzzles. A sampled position is kept only
when the project's existing prover (:func:`chesspuzzleforge.engine.forced_mate_move`,
the same exhaustive search the verifier and the PGN miner trust) finds a
forced mate in EXACTLY the requested number of moves: present at depth N and
absent at depth N-1, so a "mate in 2" is never a disguised mate in 1. Every
accepted candidate is then re-proven through
:func:`chesspuzzleforge.verifier.verify_puzzle` before it is returned - the same
accept gate the miner uses; a candidate that fails verification is never
emitted (it raises instead, because discovery and proof share the same engine
and may only disagree on a bug).

Honesty notes:

* Deterministic given a seed; unseeded runs are random (like the bank
  generator's ``seed=None``).
* ``max_tries`` bounds the total sampling work; running out fails loud with
  :class:`ValueError` rather than downgrading the goal or looping forever.
  Insufficient-material sets (e.g. ``KNK``) always exhaust the budget.
* Pawns are excluded from piece sets on purpose: they would need placement
  rules (no pawns on ranks 1/8) and promotion handling for no gain in mate
  coverage at these depths.
* Deeper requests cost more per sample (disproving mate in N-1 is the
  expensive direction), so a ``mate_in=3`` synthesis is noticeably slower
  than ``mate_in=1``; the budget, not the clock, bounds the work.
"""

from __future__ import annotations

import random

from .engine import (
    BLACK,
    WHITE,
    Board,
    file_of,
    forced_mate_move,
    move_from_uci,
    move_to_san,
    rank_of,
)
from .fen_bank import Puzzle
from .verifier import verify_puzzle

PIECE_SET_LETTERS = "QRBN"
_MAX_EXTRA_PIECES = 3
DEFAULT_MAX_TRIES = 2000

_MATE_GOALS = {1: "mate_in_1", 2: "mate_in_2", 3: "mate_in_3"}
_MATE_WORDS = {1: "one", 2: "two", 3: "three"}
_SAN_SUFFIX = {2: " (then mate next move)", 3: " (then mate within three)"}


def parse_piece_set(spec: str) -> str:
    """Validate a piece-set spec like ``KQK`` and return the white extras.

    The spec is the white king, one to three white pieces (Q/R/B/N), then the
    bare black king; case-insensitive. Returns the extras in spec order (e.g.
    ``KRRK`` -> ``"RR"``). Anything else fails loud with :class:`ValueError`.
    """
    text = spec.strip().upper()
    if len(text) < 3 or not (text.startswith("K") and text.endswith("K")):
        raise ValueError(
            f"invalid piece set {spec!r}: expected K, then 1-{_MAX_EXTRA_PIECES} "
            f"white pieces, then the bare black K (e.g. KQK, KRRK)"
        )
    extras = text[1:-1]
    if len(extras) > _MAX_EXTRA_PIECES:
        raise ValueError(
            f"invalid piece set {spec!r}: at most {_MAX_EXTRA_PIECES} white pieces "
            f"between the kings"
        )
    bad = sorted(set(extras) - set(PIECE_SET_LETTERS))
    if bad:
        raise ValueError(
            f"invalid piece set {spec!r}: unsupported piece(s) {', '.join(bad)}; "
            f"use Q, R, B or N (pawns and extra kings are not supported)"
        )
    return extras


def _sample_board(rng: random.Random, extras: str) -> Board | None:
    """Draw one uniform placement; None when it is not a legal position."""
    pieces = "K" + extras + "k"
    squares: list[int] = []
    for _ in pieces:
        while True:
            sq = rng.randrange(64)
            if sq not in squares:
                squares.append(sq)
                break
    wk, bk = squares[0], squares[-1]
    if max(abs(file_of(wk) - file_of(bk)), abs(rank_of(wk) - rank_of(bk))) <= 1:
        return None  # adjacent (or identical) kings are never legal
    cells: list[str | None] = [None] * 64
    for piece, sq in zip(pieces, squares, strict=True):
        cells[sq] = piece
    board = Board(cells, WHITE, "-", None)
    if board.is_check(BLACK):
        return None  # Black may not stand in check with White to move
    return board


def _exact_mate_key(board: Board, mate_in: int) -> str | None:
    """The prover's key move when mate is forced in exactly ``mate_in``.

    Depths are laddered cheapest-first: a position that mates quicker than
    asked is rejected before the deeper (more expensive) search ever runs.
    """
    for depth in range(1, mate_in):
        if forced_mate_move(board, depth) is not None:
            return None  # mates too quickly - not an exact mate-in-N
    return forced_mate_move(board, mate_in)


def _puzzle_id(label: str, mate_in: int, seed: int | None, index: int) -> str:
    seed_part = "" if seed is None else f"-s{seed}"
    return f"synth-{label.lower()}-m{mate_in}{seed_part}-p{index}"


def _build_puzzle(
    board: Board, label: str, mate_in: int, key: str, seed: int | None, index: int
) -> Puzzle:
    """Shape a proven position as a puzzle, mirroring the miner's output."""
    theme = f"synthesized {label} mate-in-{_MATE_WORDS[mate_in]}"
    if mate_in == 1:
        # List EVERY mating move, exactly like the miner and the generator.
        mates = [m for m in board.legal_moves() if board.push(m).is_checkmate()]
        return {
            "id": _puzzle_id(label, mate_in, seed, index),
            "fen": board.to_fen(),
            "goal": _MATE_GOALS[mate_in],
            "solution": [m.uci() for m in mates],
            "san": ", ".join(move_to_san(board, m) for m in mates),
            "theme": theme,
        }
    san = move_to_san(board, move_from_uci(board, key)) + _SAN_SUFFIX[mate_in]
    return {
        "id": _puzzle_id(label, mate_in, seed, index),
        "fen": board.to_fen(),
        "goal": _MATE_GOALS[mate_in],
        "solution": [key],
        "san": san,
        "theme": theme,
    }


def _accept(puzzle: Puzzle) -> None:
    """Re-prove a synthesized candidate through the existing verifier gate."""
    ok, message = verify_puzzle(puzzle)
    if not ok:
        raise AssertionError(
            f"synthesized puzzle {puzzle['id']} failed verification: {message}"
        )


def synthesize_puzzles(
    piece_set: str,
    mate_in: int = 2,
    count: int = 1,
    seed: int | None = None,
    max_tries: int = DEFAULT_MAX_TRIES,
) -> list[Puzzle]:
    """Synthesize ``count`` distinct, verified mate-in-``mate_in`` puzzles.

    Positions are sampled from ``piece_set`` (see :func:`parse_piece_set`);
    ``max_tries`` bounds the TOTAL number of samples across all puzzles.
    Deterministic given ``seed``; distinct puzzles never share a position.
    Raises :class:`ValueError` when the budget runs out before ``count``
    puzzles are found (a lone minor piece can never mate, for example).
    """
    extras = parse_piece_set(piece_set)
    if mate_in not in _MATE_GOALS:
        raise ValueError(f"mate_in must be 1, 2 or 3, got {mate_in}")
    if count < 1:
        raise ValueError(f"count must be >= 1, got {count}")
    if max_tries < 1:
        raise ValueError(f"max_tries must be >= 1, got {max_tries}")

    label = f"K{extras}K"
    rng = random.Random(seed)
    puzzles: list[Puzzle] = []
    emitted_fens: set[str] = set()
    for _ in range(max_tries):
        board = _sample_board(rng, extras)
        if board is None:
            continue
        fen = board.to_fen()
        if fen in emitted_fens:
            continue
        key = _exact_mate_key(board, mate_in)
        if key is None:
            continue
        puzzle = _build_puzzle(board, label, mate_in, key, seed, len(puzzles) + 1)
        _accept(puzzle)
        emitted_fens.add(fen)
        puzzles.append(puzzle)
        if len(puzzles) == count:
            return puzzles
    raise ValueError(
        f"no {_MATE_GOALS[mate_in]} found in {label} after {max_tries} samples "
        f"(found {len(puzzles)} of {count}); try a different seed, a larger "
        f"max_tries, or a stronger piece set"
    )


def synthesize_puzzle(
    piece_set: str,
    mate_in: int = 2,
    seed: int | None = None,
    max_tries: int = DEFAULT_MAX_TRIES,
) -> Puzzle:
    """Synthesize one verified mate-in-``mate_in`` puzzle from ``piece_set``."""
    return synthesize_puzzles(piece_set, mate_in, 1, seed, max_tries)[0]
