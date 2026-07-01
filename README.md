# Chess Puzzle Generator

A small, fully offline chess puzzle generator and verifier written in pure
Python. It produces and **proves** the answers to puzzles:

- **Mate in 1** (six curated positions + derive-your-own from any FEN)
- **Mate in 2** (verified by a small forced-mate search)
- **Simple tactics** — currently a "win material" puzzle (grab a hanging queen)

Each puzzle carries a position (FEN), the side to move, the solution move(s) in
UCI notation, and an ASCII board rendering. A verifier confirms every stated
solution actually delivers mate / achieves its goal, so nothing in the bank is
taken on trust.

## Why it is interesting

The core ships with its **own self-contained chess engine** (move generation,
check / checkmate / stalemate detection, and a tiny forced-mate solver) built
on the Python standard library alone. That means the whole tool — and its unit
tests — work with **zero third-party dependencies**.

The optional [`python-chess`](https://pypi.org/project/chess/) library is used
in *one* test file purely as an independent referee: it cross-checks that this
project's engine agrees with a mature reference implementation (legal moves,
checkmate detection, and the mate solutions). If `python-chess` is not
installed, that test file **skips itself cleanly** and everything else still
passes.

## Project layout

```
chess-puzzle-generator/
├── chesspuzzle/
│   ├── __init__.py       # public API re-exports
│   ├── engine.py         # pure-Python chess engine (FEN, moves, mate, ASCII)
│   ├── fen_bank.py       # curated, verified puzzle bank (zero deps)
│   ├── verifier.py       # confirms a solution achieves the puzzle goal
│   ├── generator.py      # derive puzzles from positions / draw from the bank
│   ├── cli.py            # argparse command-line interface
│   └── __main__.py       # enables `python -m chesspuzzle`
├── tests/
│   ├── test_engine.py        # engine primitives (stdlib only)
│   ├── test_fen_bank.py      # every bank puzzle verifies (stdlib only)
│   ├── test_verifier.py      # goal verification (stdlib only)
│   ├── test_generator.py     # generation + rendering (stdlib only)
│   ├── test_cli.py           # CLI entry point (stdlib only)
│   └── test_with_chess.py    # OPTIONAL cross-check vs python-chess (skips if absent)
├── conftest.py           # makes the package importable under bare `pytest`
├── requirements.txt      # optional deps (pytest, chess) — core needs neither
├── .gitignore
└── README.md
```

## Setup

The tool itself needs **nothing but Python 3.9+**. A virtual environment is only
useful for installing the dev/test extras (`pytest`, and optionally `chess`).

Windows (Git Bash / MSYS) or macOS / Linux:

```bash
cd "chess-puzzle-generator"
python -m venv .venv

# Activate the environment:
#   Git Bash / macOS / Linux:
source .venv/Scripts/activate      # on macOS/Linux: source .venv/bin/activate

# Install the optional test dependencies:
pip install -r requirements.txt
```

Prefer not to make a venv? You can still run the app directly with the system
Python — the shipped tool imports only the standard library.

## Run the app

From the project folder:

```bash
# A random puzzle (solution hidden):
python -m chesspuzzle

# A random mate-in-1, solution revealed, reproducible via a seed:
python -m chesspuzzle --goal mate_in_1 --seed 5 --reveal

# Restrict to a type: mate_in_1 | mate_in_2 | win_material
python -m chesspuzzle --goal mate_in_2 --reveal

# Derive the mate-in-1 for ANY position you supply (quote the FEN):
python -m chesspuzzle --fen "6k1/5ppp/8/8/8/8/8/R6K w - - 0 1" --reveal

# Inspect the bank / re-verify every puzzle with the engine:
python -m chesspuzzle --list
python -m chesspuzzle --verify-all
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

## Test

```bash
cd "chess-puzzle-generator"
python -m pytest -q
```

Latest local run: **91 passed** (all cross-checks included, `python-chess`
installed).

- Core-only (no third-party libs at all):
  `python -m pytest -q --ignore=tests/test_with_chess.py` → **57 passed**.
- When `python-chess` is absent, `tests/test_with_chess.py` reports
  **1 skipped** instead of failing (it uses `pytest.importorskip`).

## Architecture note

- **`engine.py`** is the foundation: an immutable-ish `Board` that parses/emits
  FEN, generates fully *legal* moves (including castling, en passant and
  promotions), and detects check / checkmate / stalemate. `forced_mate_move`
  is a tiny exhaustive minimax used for the "mate in N" logic. Its correctness
  is pinned by a Kiwipete perft(1) = 48 assertion and by cross-checks against
  `python-chess`.
- **`fen_bank.py`** is a list of plain dicts (id, FEN, goal, UCI solution(s),
  human-readable SAN, theme). No answer is trusted blindly — the test suite
  re-derives/re-verifies each one with the engine.
- **`verifier.py`** confirms a candidate move achieves a puzzle's goal: mate in
  1/2 via the search, or "win material" via a 2-ply capture evaluation that
  accounts for the opponent's best recapture.
- **`generator.py`** can *derive* a mate-in-1 puzzle from a raw position
  (`derive_mate_in_1`) or draw a validated one from the bank
  (`generate_puzzle`), and renders puzzles for the CLI.
- **`cli.py`** is a thin argparse front end.

### Fallback behaviour (important)

The requirement was to prefer `python-chess` but degrade gracefully if it will
not install. This project takes the **robust path**: the mate/tactic logic is
implemented directly in the bundled engine, so **the tool never depends on
`python-chess` at all**. If the library is present it is used only to
*independently validate* the engine (belt and braces); if it is missing, the
generator, verifier, CLI and all core tests continue to work unchanged, backed
by the curated + engine-verified FEN bank.

## Safety / privacy notes

- 100% offline. No network calls, no external services, no telemetry.
- No data is written anywhere except what you print to your own terminal.
- No secrets, credentials, or personal data are involved.
- Deterministic and reproducible (`--seed`), suitable for CI.

## Roadmap

**V2**
- More tactical motifs verified from first principles: forks, pins, skewers,
  discovered attacks, back-rank shots, and mate-in-3.
- Difficulty scoring (branching factor / solution length / material swing) and
  a `--difficulty` filter.
- Interactive "solve" mode: read the user's move from stdin and check it, with
  hints and retries.
- SAN input/output everywhere (accept `Qd8#` as well as `d1d8`).
- Export puzzles to PGN and to a JSON/SQLite puzzle store.

**V3**
- A puzzle *generator* that mines mates/tactics from a large game/position
  corpus and auto-tags themes.
- Optional Stockfish/UCI backend for deep tactic verification and rich
  difficulty calibration (kept strictly offline, opt-in).
- A minimal local web UI (isolated so the tested core stays dependency-free)
  with a draggable board and a daily-puzzle mode.
- Spaced-repetition training that tracks which motifs a user struggles with.
```
