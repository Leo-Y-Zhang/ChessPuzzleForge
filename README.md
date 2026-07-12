# Palamedes - engine-verified chess puzzle generator (pure Python, zero deps)

[![CI](https://github.com/GreenPandaTech/Palamedes/actions/workflows/ci.yml/badge.svg)](https://github.com/GreenPandaTech/Palamedes/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
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
- **Mate in 2 / 3** — confirmed by a small exhaustive forced-mate search
- **Win material** — a "grab the hanging piece" tactic checked 2 ply deep,
  accounting for the opponent's best recapture
- **Tactics** — forks (engine-proven), pins, and skewers, exposed via the API

Each puzzle carries a position (FEN), the side to move, the solution move(s) in
UCI notation, a human-readable SAN, and an ASCII board rendering.

## Why it is interesting

The core is a **self-contained chess engine** written from scratch on the
standard library: FEN parsing/emitting, fully legal move generation (castling,
en passant, promotions), check / checkmate / stalemate detection, and a small
exhaustive `forced_mate_move` solver for the "mate in N" logic.

Correctness is not asserted, it is pinned. Move generation is checked against
published **perft** node counts across several standard positions (startpos,
Kiwipete, and more), and an *optional*
test file uses [`python-chess`](https://pypi.org/project/chess/) purely as an
independent referee — cross-checking legal moves, checkmate detection, and the
mate solutions against a mature implementation. That referee is the only
third-party code anywhere near the project, it is dev/test-only, and if it is
not installed the test file skips itself cleanly (nothing in the shipped tool
imports it).

## What's new in v2

v2 deepens the verified core - every addition is proven or cross-checked, and the
tool stays offline and zero-dependency:

- **Perft harness** - move generation is pinned against known reference node counts
  (startpos, Kiwipete, and more): a strong, position-independent correctness check.
- **SAN parsing** - accept moves as `Qd8#` as well as UCI, round-tripped against the
  renderer and cross-checked with `python-chess`.
- **Mate in 3** - the exhaustive solver generalises, with a verified mate-in-3 bank puzzle.
- **Verified tactics** - `find_forks` reports a fork only when an engine capture search
  PROVES the material win; `find_pins` / `find_skewers` detect line tactics (absolute
  pins cross-checked with `python-chess`).
- **Difficulty** - a deterministic `difficulty(puzzle)` score + band and a
  `--difficulty easy|medium|hard` generation filter.
- **Solve mode** - `--solve` reads your move (SAN or UCI) and checks it, with a hint.
- **Export** - deterministic JSON and PGN for any puzzle.

## Quickstart

Requires **Python 3.11+**. There is nothing to install to run the tool — it is
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

# Filter by difficulty band, or solve interactively:
python -m palamedes --goal mate_in_2 --difficulty hard --reveal
python -m palamedes --seed 5 --solve      # type your move as SAN (Qd8#) or UCI (d1d8)
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

- Full suite, `python-chess` installed: **203 passed**.
- Core only, no third-party libs:
  `python -m pytest -q --ignore=tests/test_with_chess.py` → **137 passed**.
- With `python-chess` absent, `tests/test_with_chess.py` reports **1 skipped**
  rather than failing (it uses `pytest.importorskip("chess")`). The suite is also
  linted with **ruff** and type-checked with **mypy --strict** in CI.

CI runs the full suite on Python 3.11, 3.12, and 3.13 (see
[`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## Project layout

```
Palamedes/
├── palamedes/
│   ├── __init__.py       # public API re-exports
│   ├── engine.py         # pure-Python chess engine (FEN, moves, perft, SAN, mate)
│   ├── fen_bank.py       # curated, verified puzzle bank, typed (zero deps)
│   ├── verifier.py       # confirms a solution achieves the puzzle goal
│   ├── generator.py      # derive puzzles from positions / draw from the bank
│   ├── tactics.py        # engine-verified forks + geometric pins / skewers
│   ├── difficulty.py     # deterministic difficulty score + band
│   ├── export.py         # deterministic JSON / PGN export
│   ├── cli.py            # argparse command-line interface (+ --difficulty, --solve)
│   └── __main__.py       # enables `python -m palamedes`
├── tests/                # engine, bank, verifier, generator, cli, perft, san,
│   │                     # mate3, tactics, difficulty, export, golden, hostile,
│   │                     # perf, version — stdlib only
│   └── test_with_chess.py    # OPTIONAL cross-check vs python-chess (skips if absent)
├── pyproject.toml        # ruff + mypy --strict config
├── conftest.py           # makes the package importable under bare `pytest`
├── requirements.txt      # optional dev deps (pytest, chess) — core needs neither
└── README.md
```

## How it fits together

- **`engine.py`** — an immutable-ish `Board` that parses/emits FEN, generates
  fully *legal* moves, parses SAN (`parse_san`), and detects
  check / checkmate / stalemate. `forced_mate_move` is a small exhaustive minimax
  used for the "mate in N" logic, and `perft` counts nodes for the correctness
  harness. Correctness is pinned by reference perft counts and by the optional
  `python-chess` cross-checks.
- **`tactics.py`** — `find_forks` (reported only when a capture search proves the
  material win), `find_pins`, and `find_skewers`.
- **`difficulty.py`** / **`export.py`** — deterministic difficulty scoring and
  JSON / PGN export.
- **`fen_bank.py`** — 10 curated puzzles (6 mate-in-1, 2 mate-in-2, 1 mate-in-3,
  1 win-material) as typed dicts (id, FEN, goal, UCI solution(s), SAN, theme). No
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
  (mate in 1 to 3). It is not a general-strength search.
- Tactic detection (`find_forks` / `find_pins` / `find_skewers`) uses a shallow
  material capture search and geometric ray analysis; it finds the common motifs
  it is designed for, not every tactic in a position.
- The bank is small (a handful of hand-curated positions). New puzzles either
  come from the bank or are derived mate-in-1s from a FEN you supply; there is no
  mining from a game corpus yet.

## Safety / privacy

- 100% offline: no network calls, no external services, no telemetry.
- Nothing is written to disk beyond what you print to your own terminal.
- Deterministic and reproducible (`--seed`), suitable for CI.

## Roadmap

**Delivered in v2**: verified forks, pins and skewers; mate-in-3; a perft
correctness harness; SAN input; deterministic difficulty scoring + `--difficulty`;
an interactive `--solve` mode; and deterministic PGN/JSON export.

**Next**
- More motifs (discovered attacks, back-rank shots, deeper mates) and a larger,
  mined puzzle set with auto-tagged themes.
- A SQLite puzzle store and richer difficulty calibration.

**V3**
- Mine mates/tactics from a large game/position corpus and auto-tag themes.
- Optional Stockfish/UCI backend for deeper verification (kept offline, opt-in).
- A minimal local web UI (isolated so the tested core stays dependency-free).
- Spaced-repetition training keyed to the motifs a user struggles with.
