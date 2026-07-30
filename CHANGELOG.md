# Changelog

All notable changes to Palamedes are documented here. The project's promise is
that every answer is **proven** by its own bundled chess engine, never trusted
from a static answer key.

The format follows [Keep a Changelog](https://keepachangelog.com/); this project
uses [Semantic Versioning](https://semver.org/).

## [2.1.0] - 2026-07-30

PGN corpus mining: derive verified puzzles from real games. Pure standard
library, deterministic, and fail-loud throughout; zero runtime dependencies
preserved.

### Added

- **Mainline PGN reader** (`read_games`): tag-pair headers, movetext with move
  numbers, brace and semicolon comments, `$n` annotation glyphs, `!`/`?` move
  suffixes, results, and multiple games per file. Parenthesised variations
  (including nested ones) are skipped - mainline only, by design. Malformed
  input raises `PgnError` naming the game and line; the reader never silently
  misparses.
- **Mining pipeline** (`mine_pgn` / `mine_games`, CLI `--mine games.pgn`):
  replays each game through `parse_san`, and at every position runs cheap
  prefilters (checks available, mating material, men on board, forcing-check
  reply counts) before the expensive searches - the mate-in-1 scan,
  `forced_mate_move` at depths 2-3, and `find_forks`. Every candidate is
  deduped by position and re-verified through `verify_puzzle` before it is
  emitted; a fork is emitted only when the verifier's recapture model proves
  the gain. Output is deterministic (discovery order, `puzzle_to_json` lines);
  `--max-games` / `--max-plies` bound the work and progress goes to stderr.
  Recall is best-effort by design (prefilters trade recall for speed; a
  quiet-first-move mate in a heavy middlegame is missed) - soundness is not:
  the five-game test fixture mines 8 puzzles, each pinned exactly, in about
  2 seconds of pure Python.

### Fixed

- `render_puzzle` now labels `mate_in_3` puzzles as "Mate in 3" instead of
  leaking the raw goal string.
- README no longer claims a 3.11/3.12/3.13 CI matrix; CI runs a single
  validated version (3.13) to stay within free-tier minutes, as `ci.yml`
  always did.

## [2.0.0] - 2026-07-12

A large, fully additive expansion of the verified core. The v1 API and CLI are
unchanged; every addition is pure, deterministic, fail-loud on bad input, and
either engine-proven or cross-checked against `python-chess`. Zero runtime
dependencies preserved (`python-chess` stays a dev/test-only referee).

### Added

- **Perft harness** (`perft`): a move-generation node counter pinned against
  published reference counts (startpos to depth 3, Kiwipete, and other standard
  positions) - a strong, position-independent correctness guarantee.
- **SAN parsing** (`parse_san`): parse Standard Algebraic Notation into a legal
  move (full disambiguation, captures, promotions, castling, en passant, check
  suffixes), round-tripped against the renderer and cross-checked with
  `python-chess`.
- **Mate in 3**: the exhaustive forced-mate solver generalises to depth 3, with a
  new engine-verified mate-in-3 bank puzzle, verifier goal, and CLI goal.
- **Verified tactics** (`tactics`): `find_forks` reports a fork only when a short
  engine capture search PROVES the material win (a refuted "fork" is never
  reported); `find_pins` / `find_skewers` detect line tactics geometrically, with
  absolute pins cross-checked against `python-chess`. New `Board.attacks_from`
  primitive.
- **Difficulty** (`difficulty`): a pure, deterministic score + band from forcing
  depth, branching, and key-move rarity, plus a `--difficulty easy|medium|hard`
  generation filter.
- **Interactive solve mode** (`--solve`): reads a move as SAN or UCI, checks it
  with the engine, and gives a hint; the input is injectable for testing.
- **Export** (`puzzle_to_json`, `puzzle_to_pgn`): deterministic JSON and valid PGN
  for any puzzle (no wall-clock in the output; PGNs parse with `python-chess`).
- **Tooling & guarantees**: `pyproject.toml` with ruff + mypy `--strict`, CI lint
  and type steps, a golden-digest determinism tripwire, a hostile-input sweep, and
  a perft perf-sanity check.

### Changed

- `requires-python` raised to `>=3.11` to match the CI matrix and the ruff/mypy
  targets (the project is now type-checked under `mypy --strict`).

## [1.0.0]

- Initial release: a self-contained, from-scratch pure-Python chess engine (FEN,
  fully legal move generation, check/checkmate/stalemate, a forced-mate solver),
  a curated verified puzzle bank, a goal verifier, a puzzle generator, and a CLI -
  all with zero runtime dependencies and an optional `python-chess` cross-check.
