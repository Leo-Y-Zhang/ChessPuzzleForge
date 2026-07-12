# Palamedes "to the max" spec — targeting v2.0.0

Repo max-upgrades program #15 (after Lynceus #14). Palamedes is ALREADY v1.0.0
(tagged), so to-the-max targets **v2.0.0**. Pure-Python, ZERO runtime dependencies;
the distinctive moat is an **engine-verified** chess puzzle generator — it ships its
own from-scratch chess engine and PROVES every answer (no trusted answer key; each
solution is re-derived/re-checked by the engine). `python-chess` is a DEV/TEST-ONLY
independent referee (optional, importorskip — nothing shipped imports it).

## The hard gate (correctness + honesty) — the review lens

- **Engine-verified correctness FOREVER.** Never emit an illegal move, an unverified
  puzzle, or a "mate in N" that is not actually mate. Move generation stays pinned by
  PERFT against known reference values; every generated tactic is re-verified by the
  engine; the optional `python-chess` cross-check must keep agreeing.
- **Zero runtime dependencies.** The shipped core (engine/verifier/generator/bank/CLI)
  imports only the standard library. `python-chess` stays dev/test-only + importorskip.
- **Deterministic / reproducible.** Same `--seed` -> same puzzle; no wall-clock, no
  unseeded randomness in results. A golden digest pins a canonical generated set.
- **Offline.** No network, no external services, no telemetry, no disk writes beyond
  what the user prints.
- **Fail-loud.** Invalid FEN / illegal moves / malformed input raise a clear
  `ValueError` (never a silent wrong guess or an unhandled traceback).
- **Additive / back-compat.** The v1 public API and CLI stay unchanged; every addition
  is opt-in.

## v1 core (all pure stdlib)
`engine.py` (Board: FEN parse/emit, ASCII, legal move gen incl castling/en-passant/
promotion, check/checkmate/stalemate, `forced_mate_move` exhaustive mate-in-1/2);
`fen_bank.py` (9 curated verified puzzles); `verifier.py` (mate-in-1/2 + win-material
2-ply); `generator.py` (`derive_mate_in_1`, `generate_puzzle`, rendering); `cli.py`
(argparse). Baseline: 62 core tests + `test_with_chess.py` referee (total 109 with
`chess` installed). Pins: Kiwipete perft(1)=48.

## Build order (steps) — concentrate on the verified engine/tactics core

- **Step 0 — Tooling.** New pyproject.toml with ruff (E/F/W/I/UP/B/SIM) + mypy --strict
  (fix the ~14 existing strict errors + any UP/lint nits); CI += ruff + mypy steps
  (matrix 3.11/3.12/3.13 exists); a baseline invariant test (perft(1)=48 + import-purity
  = importing palamedes never needs `chess`). Zero runtime deps preserved.
- **Step 1 — Perft correctness harness.** A real `perft(board, depth)` + a TABLE of
  known reference perft values (startpos 1-3, Kiwipete 1-2, a couple of standard
  positions) as a strong move-generation pin — far beyond the single perft(1)=48.
- **Step 2 — SAN parse (accept SAN input).** `parse_san(board, san)` with full
  disambiguation (file/rank/both), captures, promotions, castling, +/# suffixes;
  round-trips with the existing SAN renderer; cross-checked vs python-chess.
- **Step 3 — Mate-in-3 search.** Generalise the exhaustive mate solver to
  `forced_mate_in_n` (n up to 3), perf-bounded; enables verified mate-in-3 puzzles.
- **Step 4 — Verified motif: forks.** `find_forks` — a move creating a double attack
  on 2+ pieces the opponent cannot all save, with net material gain — verified from
  first principles by the engine (and cross-checked). Never a claimed fork that isn't.
- **Step 5 — Verified motifs: pins & skewers.** `find_pins` / `find_skewers`
  (absolute/relative pins; skewers) verified geometrically AND by the engine.
- **Step 6 — Difficulty scoring + filter.** A pure `difficulty(puzzle)` (solution
  length + branching factor at the key move + material swing + motif) and a
  `--difficulty` generation filter. Deterministic, documented.
- **Step 7 — Interactive solve mode + SAN input in the CLI.** A `solve` mode reads a
  move (UCI or SAN via Step 2), checks it, and gives a hint; additive, back-compat.
- **Step 8 — Export + golden digest + hostile-input sweep + perf.** Deterministic PGN
  and JSON export of a puzzle; a golden digest of a canonical seeded generated set; a
  hostile-input sweep (bad FEN/move -> fail-loud); a perf-sanity bound on perft / the
  mate search.
- **Step 9 — Docs + version 2.0.0 + final adversarial 3-lens review + merge + tag.**
  README v2 + CHANGELOG (keep the "proves every answer" framing), `__version__` +
  pyproject 2.0.0 in lockstep (lockstep test), final review (correctness / robustness /
  determinism), merge `--no-ff` to main + tag v2.0.0.

## Rules
GreenPandaTech noreply; repo PRIVATE; proprietary licence preserved; zero runtime deps;
verify each increment with bare `.venv/Scripts/python -m pytest -q` (+ ruff + mypy
--strict once configured); the FULL suite needs `python-chess` (dev-only, importorskip
skips cleanly without it); adversarial review before merge; merge `--no-ff` + tag
v2.0.0 at the end. CI = bare `pytest` (root conftest makes `import palamedes` resolve).
Commit messages plain ASCII (no apostrophes/backticks/parens-imbalance).
