"""Command-line interface for the Chess Puzzle Generator.

Examples
--------
Print a random puzzle (position hidden solution)::

    python -m chesspuzzleforge

Print a random mate-in-1 and immediately reveal the answer::

    python -m chesspuzzleforge --goal mate_in_1 --reveal

Deterministic puzzle (useful for demos/tests)::

    python -m chesspuzzleforge --seed 7 --reveal

Derive the mate-in-1 for an arbitrary position of your own::

    python -m chesspuzzleforge --fen "6k1/5ppp/8/8/8/8/8/R6K w - - 0 1" --reveal

List every puzzle in the bank::

    python -m chesspuzzleforge --list

Mine verified puzzles from the games in a PGN file (JSON lines on stdout)::

    python -m chesspuzzleforge --mine games.pgn --max-games 100 > mined.jsonl

Synthesize a fresh, verified mate-in-2 from a bounded piece set::

    python -m chesspuzzleforge --synth KRK --seed 7 --reveal
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

from .engine import Board, Move, move_from_uci, parse_san, parse_square, square_name
from .export import puzzle_to_json
from .fen_bank import Puzzle, all_puzzles
from .generator import generate_puzzle, make_puzzle_from_position, render_puzzle
from .miner import mine_pgn
from .synth import DEFAULT_MAX_TRIES, synthesize_puzzles
from .verifier import verify_puzzle, verify_solution

GOALS = ("mate_in_1", "mate_in_2", "mate_in_3", "win_material")
_SYNTH_DEPTHS = {"mate_in_1": 1, "mate_in_2": 2, "mate_in_3": 3}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chesspuzzleforge",
        description="Generate and verify offline chess puzzles (mate-in-1/2, tactics).",
    )
    parser.add_argument(
        "--goal",
        choices=GOALS,
        help="restrict to a puzzle type (default: any).",
    )
    parser.add_argument(
        "--difficulty",
        choices=("easy", "medium", "hard"),
        help="restrict to a difficulty band (default: any).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="seed the random choice for a reproducible puzzle.",
    )
    parser.add_argument(
        "--reveal",
        action="store_true",
        help="print the solution as well as the position.",
    )
    parser.add_argument(
        "--solve",
        action="store_true",
        help="interactive: read your move (SAN or UCI) and check it.",
    )
    parser.add_argument(
        "--fen",
        help="derive a mate-in-1 puzzle from this position instead of the bank.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="list every puzzle in the built-in bank and exit.",
    )
    parser.add_argument(
        "--verify-all",
        action="store_true",
        help="verify every bank puzzle with the engine and exit.",
    )
    parser.add_argument(
        "--mine",
        metavar="PGN",
        help="mine engine-verified puzzles from the games in this PGN file "
        "(one JSON puzzle per stdout line; progress on stderr).",
    )
    parser.add_argument(
        "--max-games",
        type=int,
        default=None,
        help="with --mine: mine at most this many games from the file.",
    )
    parser.add_argument(
        "--max-plies",
        type=int,
        default=None,
        help="with --mine: replay at most this many plies of each game.",
    )
    parser.add_argument(
        "--synth",
        metavar="PIECES",
        help="synthesize a fresh, engine-verified mate puzzle from this bounded "
        "piece set (K plus 1-3 of QRBN plus the bare black king, e.g. KQK, KRK, "
        "KRRK); composes with --goal mate_in_1|mate_in_2|mate_in_3 (default "
        "mate_in_2) and --seed.",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=None,
        help="with --synth: emit this many distinct puzzles as JSON lines "
        "instead of rendering one.",
    )
    parser.add_argument(
        "--tries",
        type=int,
        default=None,
        help="with --synth: sample at most this many positions before giving up "
        f"(default {DEFAULT_MAX_TRIES}).",
    )
    return parser


def _cmd_list() -> int:
    for p in all_puzzles():
        print(f"{p['id']:24s} {p['goal']:13s} {p.get('theme', '')}")
    return 0


def _cmd_verify_all() -> int:
    all_ok = True
    for p in all_puzzles():
        ok, message = verify_puzzle(p)
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_ok = False
        print(f"{status}  {p['id']:24s} {message}")
    print("\nAll puzzles verified." if all_ok else "\nSome puzzles FAILED verification.")
    return 0 if all_ok else 1


def _cmd_mine(path: str, max_games: int | None, max_plies: int | None) -> int:
    try:
        # utf-8-sig strips the BOM that Windows editors prepend to UTF-8 files
        # (and reads plain UTF-8 unchanged). Undecodable bytes (e.g. a Latin-1
        # corpus) are a clean read error, never a traceback.
        text = Path(path).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Cannot read PGN file: {exc}", file=sys.stderr)
        return 2
    try:
        puzzles = mine_pgn(
            text,
            max_games=max_games,
            max_plies=max_plies,
            progress=lambda line: print(line, file=sys.stderr),
        )
    except ValueError as exc:  # PgnError is a ValueError: malformed or illegal PGN
        print(f"Mining failed: {exc}", file=sys.stderr)
        return 2
    for puzzle in puzzles:
        print(puzzle_to_json(puzzle))
    print(f"Mined {len(puzzles)} verified puzzles.", file=sys.stderr)
    return 0


def _read_move(board: Board, raw: str) -> Move | None:
    """Parse ``raw`` as a legal move, accepting SAN (Qd8#) or UCI (d1d8)."""
    text = raw.strip()
    if not text:
        return None
    for parse in (parse_san, move_from_uci):
        try:
            return parse(board, text)
        except (ValueError, TypeError):
            continue
    return None


def _cmd_solve(puzzle: Puzzle, reader: Callable[[str], str]) -> int:
    print(render_puzzle(puzzle, reveal=False))
    print("\nEnter your move as SAN (e.g. Qd8#) or UCI (e.g. d1d8):")
    try:
        raw = reader("> ")
    except (EOFError, KeyboardInterrupt):
        print("\nNo move entered.")
        return 1

    board = Board.from_fen(puzzle["fen"])
    move = _read_move(board, raw)
    if move is None:
        print(f"{raw.strip()!r} is not a legal move here. Try SAN (Qd8#) or UCI (d1d8).",
              file=sys.stderr)
        return 2

    ok, message = verify_solution(puzzle, move.uci())
    if ok:
        print(f"Correct! {message}.")
        return 0

    hint = ""
    solution = puzzle.get("solution") or []
    if solution:
        from_sq = parse_square(solution[0][:2])
        hint = f" Hint: the key move is by the piece on {square_name(from_sq)}."
    print(f"Not the solution: {message}.{hint}")
    return 0


def main(argv: list[str] | None = None, reader: Callable[[str], str] = input) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    # An explicitly given empty string ("--synth \"\"") must fail loud like any
    # other bad value, never truthiness-skip its branch and fall through to the
    # bank generator - hence "is not None" rather than bare truth tests below.
    if (args.max_games is not None or args.max_plies is not None) and args.mine is None:
        parser.error("--max-games and --max-plies require --mine")
    if (args.count is not None or args.tries is not None) and args.synth is None:
        parser.error("--count and --tries require --synth")
    if args.count is not None and (args.solve or args.reveal):
        parser.error("--count emits JSON lines; it cannot be combined with --solve or --reveal")
    if args.synth is not None:
        if args.mine is not None or args.fen is not None:
            parser.error("--synth cannot be combined with --mine or --fen")
        if args.difficulty:
            parser.error("--difficulty filters the bank; it does not apply to --synth")
        if args.goal is not None and args.goal not in _SYNTH_DEPTHS:
            parser.error("--synth generates mate puzzles; use --goal mate_in_1|mate_in_2|mate_in_3")

    if args.list:
        return _cmd_list()
    if args.verify_all:
        return _cmd_verify_all()
    if args.mine is not None:
        return _cmd_mine(args.mine, args.max_games, args.max_plies)

    if args.synth is not None:
        # Default to mate in 2: deep enough to be a real puzzle, cheap to find.
        mate_in = _SYNTH_DEPTHS[args.goal or "mate_in_2"]
        try:
            puzzles = synthesize_puzzles(
                args.synth,
                mate_in=mate_in,
                count=args.count if args.count is not None else 1,
                seed=args.seed,
                max_tries=args.tries if args.tries is not None else DEFAULT_MAX_TRIES,
            )
        except ValueError as exc:
            print(f"Synthesis failed: {exc}", file=sys.stderr)
            return 2
        if args.count is not None:
            for p in puzzles:
                print(puzzle_to_json(p))
            print(f"Synthesized {len(puzzles)} verified puzzles.", file=sys.stderr)
            return 0
        puzzle = puzzles[0]
    elif args.fen is not None:
        try:
            derived = make_puzzle_from_position(args.fen)
        except ValueError as exc:
            print(f"Invalid FEN: {exc}", file=sys.stderr)
            return 2
        if derived is None:
            print("No mate-in-1 found in that position.", file=sys.stderr)
            return 2
        puzzle = derived
    else:
        try:
            puzzle = generate_puzzle(
                goal=args.goal, seed=args.seed, difficulty=args.difficulty
            )
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2

    if args.solve:
        return _cmd_solve(puzzle, reader)

    print(render_puzzle(puzzle, reveal=args.reveal))
    if not args.reveal:
        print("\n(Run again with --reveal to see the solution.)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
