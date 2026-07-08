# Palamedes - engine-verified chess puzzle generator (pure Python, zero deps)

[![CI](https://github.com/GreenPandaTech/Palamedes/actions/workflows/ci.yml/badge.svg)](https://github.com/GreenPandaTech/Palamedes/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![Dependencies](https://img.shields.io/badge/runtime%20deps-none-brightgreen)

Palamedes (the mythical Greek inventor of board games) is an offline chess
puzzle generator that ships with its own chess engine and **proves** every
answer it gives you. It does not store a pre-baked answer key and hope it is
right: each puzzle's solution is re-derived and re-checked by a bundled
forced-mate search, so the tool cannot serve a "mate in 1" that is not actually
mate. The whole thing — engine, verifier, generator, CLI, and their tests —
runs on the Python standard library with **no runtime dependencies**.

Puzzle types:

- **Mate in 1** — draw from the curated bank, or derive one for any FEN you pass
- **Mate in 2** — confirmed by a small exhaustive forced-mate search
- **Win material** — a "grab the hanging piece" tactic checked 2 ply deep,
  accounting for the opponent's best recapture

Each puzzle carries a position (FEN), the side to move, the solution move(s) in
UCI notation, a human-readable SAN, and an ASCII board rendering.

## Why it is interesting

The core is a **self-contained chess engine** written from scratch on the
standard library: FEN parsing/emitting, fully legal move generation (castling,
en passant, promotions), check / checkmate / stalemate detection, and a small
exhaustive `forced_mate_move` solver for the "mate in N" logic.

Correctness is not asserted, it is pinned. Move generation is checked against a
known reference value (Kiwipete perft(1) = 48 legal moves), and an *optional*
test file uses [`python-chess`](https://pypi.org/project/chess/) purely as an
independent referee — cross-checking legal moves, checkmate detection, and the
mate solutions against a mature implementation. That referee is the only
third-party code anywhere near the project, it is dev/test-only, and if it is
not installed the test file skips itself cleanly (nothing in the shipped tool
imports it).

## Quickstart

Requires **Python 3.9+**. There is nothing to install to run the tool — it is
not published to PyPI and imports only the standard library, so you run it in
place with `python -m palamedes`.

```bash
git clone https://github.com/GreenPandaTech/Palamedes.git
cd Palamedes

# A random puzzle, solution hidden:
python -m palamedes

# A random mate-in-1, solution revealed, reproducible via a seed:
python -m palamedes --goal mate_in_1 --seed 5 --reveal

# Pick a type: mate_in_1 | mate_in_2 | win_material
python -m palamedes --goal mate_in_2 --reveal

# Derive the mate-in-1 for ANY position you supply (quote the FEN):
python -m palamedes --fen "6k1/5ppp/8/8/8/8/8/R6K w - - 0 1" --reveal

# Inspect the bank / re-verify every puzzle with the engine:
python -m palamedes --list
python -m palamedes --verify-all
```

Example output:

```
Puzzle: m1-queen-escort
Theme:  queen-and-king mate
Goal:   Mate in 1  (White to move)

  +------------------------+
8 | . . . . . . k . |
...
1 | . . . Q . . . . |
  +------------------------+
    a b c d e f g h

FEN: 6k1/8/6K1/8/8/8/8/3Q4 w - - 0 1

Solution: Qd8#  (UCI: d1d8)
```

## Tests

The optional test extras (`pytest`, and the `python-chess` referee) install
from `requirements.txt`:

```bash
python -m venv .venv
source .venv/Scripts/activate   # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
```

Test counts (local, Python 3.13):

- Full suite, `python-chess` installed: **109 passed**.
- Core only, no third-party libs:
  `python -m pytest -q --ignore=tests/test_with_chess.py` → **62 passed**.
- With `python-chess` absent, `tests/test_with_chess.py` reports **1 skipped**
  rather than failing (it uses `pytest.importorskip("chess")`).

CI runs the full suite on Python 3.11, 3.12, and 3.13 (see
[`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## Project layout

```
Palamedes/
├── palamedes/
│   ├── __init__.py       # public API re-exports
│   ├── engine.py         # pure-Python chess engine (FEN, moves, mate, ASCII)
│   ├── fen_bank.py       # curated, verified puzzle bank (zero deps)
│   ├── verifier.py       # confirms a solution achieves the puzzle goal
│   ├── generator.py      # derive puzzles from positions / draw from the bank
│   ├── cli.py            # argparse command-line interface
│   └── __main__.py       # enables `python -m palamedes`
├── tests/
│   ├── test_engine.py        # engine primitives (stdlib only)
│   ├── test_fen_bank.py      # every bank puzzle verifies (stdlib only)
│   ├── test_verifier.py      # goal verification (stdlib only)
│   ├── test_generator.py     # generation + rendering (stdlib only)
│   ├── test_cli.py           # CLI entry point (stdlib only)
│   └── test_with_chess.py    # OPTIONAL cross-check vs python-chess (skips if absent)
├── conftest.py           # makes the package importable under bare `pytest`
├── requirements.txt      # optional dev deps (pytest, chess) — core needs neither
└── README.md
```

## How it fits together

- **`engine.py`** — an immutable-ish `Board` that parses/emits FEN, generates
  fully *legal* moves, and detects check / checkmate / stalemate.
  `forced_mate_move` is a small exhaustive minimax used for the "mate in N"
  logic. Correctness is pinned by the Kiwipete perft(1) = 48 assertion and by
  the optional `python-chess` cross-checks.
- **`fen_bank.py`** — 9 curated puzzles (6 mate-in-1, 2 mate-in-2, 1
  win-material) as plain dicts (id, FEN, goal, UCI solution(s), SAN, theme). No
  answer is trusted blindly — the test suite re-verifies each with the engine.
- **`verifier.py`** — confirms a candidate move achieves a puzzle's goal: mate
  in 1/2 via the search, or "win material" via a 2-ply capture evaluation that
  accounts for the opponent's best recapture.
- **`generator.py`** — derives a mate-in-1 from a raw position
  (`derive_mate_in_1`), draws a validated one from the bank (`generate_puzzle`),
  and renders puzzles for the CLI.
- **`cli.py`** — a thin argparse front end.

## Scope and limitations

This is a compact, self-verifying puzzle tool, not a full engine or trainer:

- The forced-mate search is exhaustive and only intended for shallow depths
  (mate-in-1 and mate-in-2). It is not a general-strength search.
- Puzzle types are limited to mate-in-1, mate-in-2, and a single win-material
  tactic. Richer motifs (forks, pins, skewers, back-rank, mate-in-3) are not
  implemented.
- The bank is small (9 hand-curated positions). New puzzles either come from
  the bank or are derived mate-in-1s from a FEN you supply; there is no mining
  from a game corpus.
- CLI input/output is UCI-oriented; SAN is shown but not accepted as input.

## Safety / privacy

- 100% offline: no network calls, no external services, no telemetry.
- Nothing is written to disk beyond what you print to your own terminal.
- Deterministic and reproducible (`--seed`), suitable for CI.

## Roadmap

**V2**
- More motifs verified from first principles: forks, pins, skewers, discovered
  attacks, back-rank shots, and mate-in-3.
- Difficulty scoring (branching factor / solution length / material swing) and
  a `--difficulty` filter.
- Interactive "solve" mode: read a move from stdin and check it, with hints.
- Accept SAN input (`Qd8#`) as well as UCI (`d1d8`).
- Export puzzles to PGN and to a JSON/SQLite store.

**V3**
- Mine mates/tactics from a large game/position corpus and auto-tag themes.
- Optional Stockfish/UCI backend for deeper verification (kept offline, opt-in).
- A minimal local web UI (isolated so the tested core stays dependency-free).
- Spaced-repetition training keyed to the motifs a user struggles with.
