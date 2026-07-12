"""Command-line interface for the Chess Puzzle Generator.

Examples
--------
Print a random puzzle (position hidden solution)::

    python -m palamedes

Print a random mate-in-1 and immediately reveal the answer::

    python -m palamedes --goal mate_in_1 --reveal

Deterministic puzzle (useful for demos/tests)::

    python -m palamedes --seed 7 --reveal

Derive the mate-in-1 for an arbitrary position of your own::

    python -m palamedes --fen "6k1/5ppp/8/8/8/8/8/R6K w - - 0 1" --reveal

List every puzzle in the bank::

    python -m palamedes --list
"""

from __future__ import annotations

import argparse
import sys

from .fen_bank import all_puzzles
from .generator import generate_puzzle, make_puzzle_from_position, render_puzzle
from .verifier import verify_puzzle

GOALS = ("mate_in_1", "mate_in_2", "mate_in_3", "win_material")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="palamedes",
        description="Generate and verify offline chess puzzles (mate-in-1/2, tactics).",
    )
    parser.add_argument(
        "--goal",
        choices=GOALS,
        help="restrict to a puzzle type (default: any).",
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list:
        return _cmd_list()
    if args.verify_all:
        return _cmd_verify_all()

    if args.fen:
        try:
            puzzle = make_puzzle_from_position(args.fen)
        except ValueError as exc:
            print(f"Invalid FEN: {exc}", file=sys.stderr)
            return 2
        if puzzle is None:
            print("No mate-in-1 found in that position.", file=sys.stderr)
            return 2
    else:
        puzzle = generate_puzzle(goal=args.goal, seed=args.seed)

    print(render_puzzle(puzzle, reveal=args.reveal))
    if not args.reveal:
        print("\n(Run again with --reveal to see the solution.)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
