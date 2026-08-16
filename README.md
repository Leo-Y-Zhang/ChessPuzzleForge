# ChessPuzzleForge - engine-verified chess puzzle generator (pure Python, zero deps)

[![CI](https://github.com/Leo-Y-Zhang/ChessPuzzleForge/actions/workflows/ci.yml/badge.svg)](https://github.com/Leo-Y-Zhang/ChessPuzzleForge/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Dependencies](https://img.shields.io/badge/runtime%20deps-none-brightgreen)

PuzzleForge is an offline chess puzzle generator that ships with its own
chess engine and **proves** every answer it gives you. It does not store a
pre-baked answer key and hope it is right: each puzzle's solution is re-derived
and re-checked by a bundled forced-mate search, so the tool cannot serve a
"mate in 1" that is not actually mate. The whole thing — engine, verifier,
generator, CLI, and their tests — runs on the Python standard library with
**no runtime dependencies**.

Puzzle types:

- **Mate in 1** — draw from the curated bank, or derive one for any FEN you pass
- **Mate in 2 / 3** — confirmed by a small exhaustive forced-mate search
- **Win material** — a "grab the hanging piece" tactic checked 2 ply deep,
  accounting for the opponent's best recapture
- **Tactics** — forks (engine-proven), pins, and skewers, exposed via the API
- **Mined from your games** — `--mine games.pgn` replays a PGN file and emits
  the verified mates and forks it finds along the mainlines (new in v2.1; see
  [Mining a real game](#mining-a-real-game) for a live session)
- **Synthesized endgames** — `--synth KQK` samples a bounded piece set until
  the engine proves an exact mate-in-N, no input file needed (new in v2.2; see
  [Synthesizing fresh endgames](#synthesizing-fresh-endgames))

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

## What's new in v2.2

**Seeded endgame synthesis.** `--synth KQK` generates a fresh puzzle instead of
drawing one from the bank or a PGN: positions are sampled uniformly from a
bounded piece set (the white king, one to three white pieces from Q/R/B/N, and
the bare black king), and a sample is kept only when the engine proves a forced
mate in EXACTLY the requested number of moves — present at depth N, absent at
N-1, so a "mate in 2" is never a disguised mate in 1. Every accepted position
is then re-proven through `verify_puzzle` before it is printed, the same accept
gate the miner uses. Deterministic given `--seed`, budget-bounded via `--tries`
(running out fails loud rather than looping forever), and `--count N` emits
JSON lines exactly like `--mine`. See
[Synthesizing fresh endgames](#synthesizing-fresh-endgames) for a live session.

## What's new in v2.1

**PGN corpus mining.** `--mine games.pgn` reads a PGN file with a stdlib-only
mainline reader (headers, comments, NAGs, nested variations skipped, results,
multiple games, move numbers spaced `1. e4` or glued `1.e4`; malformed input
fails loud naming the game and line), replays each game through `parse_san`,
and at every position runs cheap prefilters before the bounded searches: the
mate-in-1 scan; full-width `forced_mate_move` at depth 2 in positions of at
most 8 men, with a checks-only depth-2 scan in larger ones; depth 3 only at
6 men or fewer; and `find_forks` under a hard node budget. Candidates are
deduped by position and re-verified through `verify_puzzle` before being
emitted as deterministic JSON lines. Honest limits: only the mainline is
replayed, and the prefilters trade recall for speed (above 8 men a mate in 2
is found only via a checking key move, and a fork is emitted only when the
recapture model proves the gain), so some tactics in a game will be missed —
but nothing is emitted that the engine has not re-proven. Measured locally:
the five-game test fixture (8 exactly-pinned puzzles) and the full 33-ply
Opera game fixture (3 pinned puzzles, positions up to 32 men) each mine in
under a second of pure Python.

## What's new in v2

v2 deepens the verified core - every addition is proven or cross-checked, and the
tool stays offline and zero-dependency:

- **Perft harness** - move generation is pinned against known reference node counts
  (startpos, Kiwipete, and more): a strong, position-independent correctness check.
- **SAN parsing** - accept moves as `Qd8#` as well as UCI, round-tripped against the
  renderer and cross-checked with `python-chess`.
- **Mate in 3** - the exhaustive solver generalises, with a verified mate-in-3 bank puzzle.
- **Verified tactics** - `find_forks` reports a fork only when an engine capture search
  PROVES the material win (a fail-soft alpha-beta search under a hard node budget:
  a candidate it cannot prove in budget is simply not reported); `find_pins` /
  `find_skewers` detect line tactics (absolute pins cross-checked with `python-chess`).
- **Difficulty** - a deterministic `difficulty(puzzle)` score + band and a
  `--difficulty easy|medium|hard` generation filter.
- **Solve mode** - `--solve` reads your move (SAN or UCI) and checks it, with a hint.
- **Export** - deterministic JSON and PGN for any puzzle.

## Quickstart

Requires **Python 3.11+**. There is nothing to install to run the tool — it is
not published to PyPI and imports only the standard library, so you run it in
place with `python -m chesspuzzleforge`.

```bash
git clone https://github.com/Leo-Y-Zhang/ChessPuzzleForge.git
cd PuzzleForge

# A random puzzle, solution hidden:
python -m chesspuzzleforge

# A random mate-in-1, solution revealed, reproducible via a seed:
python -m chesspuzzleforge --goal mate_in_1 --seed 5 --reveal

# Pick a type: mate_in_1 | mate_in_2 | win_material
python -m chesspuzzleforge --goal mate_in_2 --reveal

# Derive the mate-in-1 for ANY position you supply (quote the FEN):
python -m chesspuzzleforge --fen "6k1/5ppp/8/8/8/8/8/R6K w - - 0 1" --reveal

# Inspect the bank / re-verify every puzzle with the engine:
python -m chesspuzzleforge --list
python -m chesspuzzleforge --verify-all

# Filter by difficulty band, or solve interactively:
python -m chesspuzzleforge --goal mate_in_2 --difficulty hard --reveal
python -m chesspuzzleforge --seed 5 --solve      # type your move as SAN (Qd8#) or UCI (d1d8)

# Mine verified puzzles from the games in a PGN file (JSON lines on stdout,
# progress on stderr); bound the work with --max-games / --max-plies:
python -m chesspuzzleforge --mine games.pgn --max-games 100 > mined.jsonl

# Synthesize a fresh, engine-proven endgame from a piece set (mate in 2 by
# default; deterministic with --seed; --count emits JSON lines like --mine):
python -m chesspuzzleforge --synth KRK --seed 7 --reveal
python -m chesspuzzleforge --synth KQK --seed 9 --count 2 > synthesized.jsonl
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

## Mining a real game

`tests/data/opera_game.pgn` is Morphy's 1858 Opera game (33 plies, full 32-man
positions). Mining it end to end:

```bash
python -m chesspuzzleforge --mine tests/data/opera_game.pgn > mined.jsonl
```

Progress goes to stderr:

```
game 1/1: replayed 33 plies, 3 new puzzles (3 total)
Mined 3 verified puzzles.
```

and `mined.jsonl` now holds the game's famous finish as three puzzles — the
exchange-winning bishop check, the queen-sacrifice mate in two, and the final
rook mate:

```json
{"fen": "4kb1r/p2r1ppp/4qn2/1B2p1B1/4P3/1Q6/PPP2PPP/2KR4 w k - 2 15", "goal": "win_material", "id": "mined-g1-p28-fork", "san": "Bxd7+", "solution": ["b5d7"], "theme": "mined bishop fork", "threshold": 2.0}
{"fen": "4kb1r/p2n1ppp/4q3/4p1B1/4P3/1Q6/PPP2PPP/2KR4 w k - 0 16", "goal": "mate_in_2", "id": "mined-g1-p30-m2", "san": "Qb8+ (then mate next move)", "solution": ["b3b8"], "theme": "mined mate-in-two"}
{"fen": "1n2kb1r/p4ppp/4q3/4p1B1/4P3/8/PPP2PPP/2KR4 w k - 0 17", "goal": "mate_in_1", "id": "mined-g1-p32-m1", "san": "Rd8#", "solution": ["d1d8"], "theme": "mined mate-in-one"}
```

Every line above was re-proven through `verify_puzzle` before it was emitted:
the miner only discovers candidates, the engine proves them. The whole command
takes about half a second measured locally on Python 3.13 (about 0.3 s of
mining; the rest is interpreter startup). Two deliberate design rules keep the
output trustworthy:

- **Mainline only.** Parenthesised variations are skipped by design, so every
  puzzle comes from a position that actually occurred in the game.
- **Fail loud.** Malformed PGN never degrades into a silently wrong replay.
  The reader names the game and move, and the CLI exits nonzero — here on a
  file whose fourth move is illegal:

  ```
  $ python -m chesspuzzleforge --mine broken.pgn
  Mining failed: game 1: move 4 ('Kd4') does not name a legal move: no legal move matches SAN 'Kd4'
  $ echo $?
  2
  ```

## Synthesizing fresh endgames

`--synth` needs no input file at all: give it a piece set and it samples
positions until the engine proves one is mate in exactly the requested number
of moves, then re-proves it through `verify_puzzle` before printing anything:

```bash
python -m chesspuzzleforge --synth KRK --seed 7 --reveal
```

```
Puzzle: synth-krk-m2-s7-p1
Theme:  synthesized KRK mate-in-two
Goal:   Mate in 2  (White to move)

  +------------------------+
8 | . . K . . . . R |
7 | k . . . . . . . |
...
  +------------------------+
    a b c d e f g h

FEN: 2K4R/k7/8/8/8/8/8/8 w - - 0 1

Solution: Rh6 (then mate next move)  (UCI: h8h6)
```

Batch mode emits JSON lines exactly like the miner (the summary goes to
stderr, never into the JSON stream), and the same seed always reproduces the
same puzzles:

```json
{"fen": "8/k7/2K5/8/8/8/8/5Q2 w - - 0 1", "goal": "mate_in_2", "id": "synth-kqk-m2-s9-p1", "san": "Qb5 (then mate next move)", "solution": ["f1b5"], "theme": "synthesized KQK mate-in-two"}
{"fen": "8/8/2Q5/8/1K6/8/8/1k6 w - - 0 1", "goal": "mate_in_2", "id": "synth-kqk-m2-s9-p2", "san": "Kb3 (then mate next move)", "solution": ["b4b3"], "theme": "synthesized KQK mate-in-two"}
```

Both commands above run in about half a second to a second and a half
measured locally on Python 3.13, interpreter startup included. Two design
rules keep the output trustworthy:

- **Exactness by laddered absence.** A candidate is accepted for mate-in-N
  only after the prover finds *no* mate at every depth below N — the expensive
  direction, but the honest one. Deeper goals therefore cost more per sample
  and the cost varies with the seed; `--tries` bounds the total work.
- **Fail loud.** Pawns are excluded from piece sets by design (they would
  need placement and promotion rules for no mate coverage gain at these
  depths), and a set that cannot mate exhausts its budget and exits nonzero
  rather than looping or downgrading the goal:

  ```
  $ python -m chesspuzzleforge --synth KPK
  Synthesis failed: invalid piece set 'KPK': unsupported piece(s) P; use Q, R, B or N (pawns and extra kings are not supported)
  $ echo $?
  2
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

- Full suite, `python-chess` installed: **293 passed**.
- Core only, no third-party libs:
  `python -m pytest -q --ignore=tests/test_with_chess.py` → **227 passed**.
- With `python-chess` absent, `tests/test_with_chess.py` reports **1 skipped**
  rather than failing (it uses `pytest.importorskip("chess")`). The suite is also
  linted with **ruff** and type-checked with **mypy --strict** in CI.

CI runs the full suite, ruff, and mypy on a single validated Python version
(3.13) to stay within free-tier minutes; `requires-python` is `>=3.11` (see
[`.github/workflows/ci.yml`](.github/workflows/ci.yml)).

## Project layout

```
PuzzleForge/
├── chesspuzzleforge/
│   ├── __init__.py       # public API re-exports
│   ├── engine.py         # pure-Python chess engine (FEN, moves, perft, SAN, mate)
│   ├── fen_bank.py       # curated, verified puzzle bank, typed (zero deps)
│   ├── verifier.py       # confirms a solution achieves the puzzle goal
│   ├── generator.py      # derive puzzles from positions / draw from the bank
│   ├── tactics.py        # engine-verified forks + geometric pins / skewers
│   ├── difficulty.py     # deterministic difficulty score + band
│   ├── export.py         # deterministic JSON / PGN export
│   ├── pgn.py            # fail-loud mainline PGN reader (stdlib only)
│   ├── miner.py          # prefiltered, verified puzzle mining over PGN games
│   ├── synth.py          # seeded, verified endgame synthesis from piece sets
│   ├── cli.py            # argparse CLI (+ --solve, --mine, --synth)
│   └── __main__.py       # enables `python -m chesspuzzleforge`
├── tests/                # engine, bank, verifier, generator, cli, perft, san,
│   │                     # mate3, tactics, difficulty, export, golden, hostile,
│   │                     # pgn, miner, cli_mine, synth, cli_synth, perf,
│   │                     # version — stdlib only
│   ├── data/mined_games.pgn  # toy mining fixture (castling + promotion + tactics)
│   ├── data/opera_game.pgn   # real-game mining fixture (full 32-man positions)
│   └── test_with_chess.py    # OPTIONAL cross-check vs python-chess (skips if absent)
├── docs/                 # PRD, TDD, App Flow, Design Brief (+ archived specs)
├── pyproject.toml        # ruff + mypy --strict config
├── conftest.py           # makes the package importable under bare `pytest`
├── requirements.txt      # optional dev deps (pytest, chess) — core needs neither
└── README.md
```

## Design documents

Written retrospectively against the shipped code, not against this README:

- [`docs/PRD.md`](docs/PRD.md) — the problem, who it is for, and what is
  deliberately out of scope.
- [`docs/TDD.md`](docs/TDD.md) — the architecture as built: data shapes, module
  contracts, the search budgets, failure modes and rollback.
- [`docs/APP_FLOW.md`](docs/APP_FLOW.md) — every CLI mode and every terminal
  state, including the error paths and their exit codes.
- [`docs/DESIGN_BRIEF.md`](docs/DESIGN_BRIEF.md) — the terminal-output design
  rules (stream discipline, ASCII-only board, no colour) and why.

## How it fits together

- **`engine.py`** — an immutable-ish `Board` that parses/emits FEN, generates
  fully *legal* moves, parses SAN (`parse_san`), and detects
  check / checkmate / stalemate. `forced_mate_move` is a small exhaustive minimax
  used for the "mate in N" logic, and `perft` counts nodes for the correctness
  harness. Correctness is pinned by reference perft counts and by the optional
  `python-chess` cross-checks.
- **`tactics.py`** — `find_forks` (reported only when a budget-bounded alpha-beta
  capture search proves the material win), `find_pins`, and `find_skewers`.
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
- **`pgn.py`** / **`miner.py`** — a fail-loud mainline PGN reader
  (`read_games`) and the mining pipeline (`mine_pgn`): replay, prefilter,
  search, dedupe by position, re-verify through `verify_puzzle`, emit.
- **`synth.py`** — seeded endgame synthesis (`synthesize_puzzles`): sample a
  bounded piece set uniformly, prove an exact mate-in-N with the engine,
  re-verify through `verify_puzzle`, emit.
- **`cli.py`** — a thin argparse front end.

## Scope and limitations

This is a compact, self-verifying puzzle tool, not a full engine or trainer:

- The forced-mate search is exhaustive and only intended for shallow depths
  (mate in 1 to 3). It is not a general-strength search.
- Tactic detection (`find_forks` / `find_pins` / `find_skewers`) uses a shallow
  material capture search (alpha-beta, capped by a hard node budget — a fork
  whose proof does not finish in budget is not reported) and geometric ray
  analysis; it finds the common motifs it is designed for, not every tactic in
  a position.
- The bank is small (a handful of hand-curated positions); beyond it, puzzles
  are derived from a FEN you supply or mined from a PGN you supply.
- Mining reads mainlines only (variations are skipped) and its prefilters trade
  recall for speed: deep mate searches run only where a check is available; above
  8 men the depth-2 search considers only checking key moves that leave at most
  4 replies (a quiet key move is then missed — this is pinned by a test); depth 3
  runs only at 6 men or fewer; and a fork is emitted only when the verifier's
  recapture model proves the gain. Some tactics present in a game will therefore
  be missed; everything emitted is engine-proven.
- Mining speed is honest pure-Python speed: the five-game test fixture and the
  33-ply Opera game fixture each mine in under a second locally, so budget
  roughly a second per full game; a large corpus is still not the target use
  case.
- Synthesis samples bounded piece sets only (the white king plus one to three
  of Q/R/B/N versus the bare black king; no pawns — they would need placement
  and promotion rules for no mate coverage gain at these depths). A set that
  cannot force the requested mate (e.g. `KNK`) exhausts its `--tries` budget
  and exits nonzero rather than looping, and deeper goals cost more per sample
  because disproving the shallower mate is the expensive direction.

## Safety / privacy

- 100% offline: no network calls, no external services, no telemetry.
- Nothing is written to disk beyond what you print to your own terminal.
- Deterministic and reproducible (`--seed`), suitable for CI.

## Roadmap

**Delivered in v2**: verified forks, pins and skewers; mate-in-3; a perft
correctness harness; SAN input; deterministic difficulty scoring + `--difficulty`;
an interactive `--solve` mode; and deterministic PGN/JSON export.

**Delivered in v2.1**: PGN corpus mining (`--mine`) - mainline replay, prefiltered
mate/fork searches, dedupe, and re-verification of every emitted puzzle.

**Delivered in v2.2**: seeded endgame synthesis (`--synth`) - uniform sampling
from bounded piece sets, exact mate-in-N proof by laddered absence, the
verifier accept gate on every emission, and deterministic JSON batch output.

**Next**
- More motifs (discovered attacks, back-rank shots, deeper mates) and richer
  auto-tagged themes for mined puzzles.
- A SQLite puzzle store and richer difficulty calibration.

**V3**
- Scale mining to large corpora (better prefilters or an optional fast backend).
- Optional Stockfish/UCI backend for deeper verification (kept offline, opt-in).
- A minimal local web UI (isolated so the tested core stays dependency-free).
- Spaced-repetition training keyed to the motifs a user struggles with.
