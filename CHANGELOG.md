# Changelog

All notable changes to Palamedes are documented here. The project's promise is
that every answer is **proven** by its own bundled chess engine, never trusted
from a static answer key.

The format follows [Keep a Changelog](https://keepachangelog.com/); this project
uses [Semantic Versioning](https://semver.org/).

## [2.2.0] - 2026-07-31

Seeded endgame synthesis: generate fresh, engine-proven mate-in-N puzzles from
nothing but a piece set. Pure standard library, deterministic, fail-loud
throughout; zero runtime dependencies preserved.

### Added

- **Endgame synthesizer** (`synthesize_puzzle` / `synthesize_puzzles`, module
  `palamedes/synth.py`): samples positions uniformly from a bounded piece set
  (the white king, one to three white pieces from Q/R/B/N, and the bare black
  king, White to move) with `random.Random(seed)`, rejects illegal placements
  (adjacent kings, defender already in check), and keeps only positions where
  the existing `forced_mate_move` prover finds mate in EXACTLY the requested
  number of moves — present at depth N and absent at every shallower depth, so
  a "mate in 2" is never a disguised mate in 1. Every accepted candidate is
  then re-proven through `verify_puzzle` before it is emitted (the same accept
  gate the miner uses); a verifier disagreement raises instead of emitting.
  Output mirrors the miner: mate-in-1 lists every mating move, deeper goals
  carry the SAN continuation suffixes. `parse_piece_set`, `synthesize_puzzle`
  and `synthesize_puzzles` are re-exported in the public API.
- **CLI synthesis mode**: `--synth KQK` composes with
  `--goal mate_in_1|mate_in_2|mate_in_3` (default `mate_in_2`), `--seed`,
  `--reveal` and `--solve`; `--count N` emits JSON lines like `--mine`
  (summary on stderr); `--tries` bounds the sampling budget (default 2000).
  Exhaustion, invalid piece sets (pawns are excluded by design), bad depths
  and bad budgets all fail loud with exit 2 and a clear message — never a
  silently downgraded goal. Measured locally (Python 3.13, end to end
  including interpreter startup): `--synth KRK --seed 7 --reveal` about 1.5 s,
  `--synth KQK --seed 9 --count 2` about 0.4 s, and
  `--synth KRRK --goal mate_in_3 --seed 0` about 0.6 s; deeper goals cost more
  per sample (disproving the shallower mate is the expensive direction) and
  the cost varies with the seed, so the budget, not the clock, bounds the
  work.
- 39 new tests (exactness, piece census, byte-identical determinism, batch
  dedupe by position, fail-loud specs, the never-emit-on-failed-verification
  gate, and every CLI mode): full suite 250 -> 289, core-only 184 -> 223.

### Fixed

- **Empty-string CLI values no longer fall through to the bank.** `--synth ""`,
  `--mine ""` and `--fen ""` used to truthiness-skip their branch and print a
  bank puzzle with exit 0; each now takes its own error path (invalid piece
  set / unreadable file / invalid FEN) and exits 2.
- **`--count` now conflicts loudly with `--solve` / `--reveal`.** The JSON
  batch mode used to silently drop the interactive flags; combining them is
  now a parser error, matching the CLI's fail-loud posture.

## [2.1.1] - 2026-07-30

Mining now handles real games at real speed. The 2.1.0 pipeline was measured
stalling for 15+ minutes on a single ordinary 32-man opening position (an
unbounded all-captures search behind `find_forks`); every search the miner
runs is now bounded, and a realistic full-length game fixture pins both the
speed and the exact output.

### Fixed

- **`find_forks` no longer hangs on full boards.** The fork proof is now a
  fail-soft alpha-beta capture search (captures ordered by falling victim
  value) under a hard node budget shared across the call. With a full window
  it returns exactly the same values as the old plain negamax — the pinned
  royal-fork and refuted-fork results are unchanged — but the position after
  1\. e4 e6 2. e5 d5 3. Nf3 c5 4. Be2 Nc6 5. O-O now takes about a
  millisecond instead of 15+ minutes. A candidate whose proof does not
  complete within the budget is treated as unproven and NOT reported
  (soundness over recall), so `find_forks` terminates in bounded time on any
  input.
- **The miner's depth-2 mate search is bounded on large boards.** At more
  than 8 men it now scans only checking key moves that leave the defender at
  most 4 replies, confirming each reply with a mate-in-1 scan; the full-width
  `forced_mate_move` search (which also catches quiet key moves) still runs
  in small positions. The recall trade — a quiet-key mate in 2 at 11 men is
  real but not emitted — is pinned by a test.
- **`verify_solution` computes the mate-goal failure hint lazily.** A correct
  mate-in-2/3 candidate is verified by checking that candidate alone, so
  re-verifying mined candidates stays cheap on full boards; the exhaustive
  whole-position search now runs only to explain a wrong answer. Messages
  are unchanged.
- **CLI `--mine` file decoding.** PGN files are read as `utf-8-sig` (a
  Windows Notepad BOM no longer surfaces as an unrecognised movetext token)
  and undecodable bytes (e.g. a Latin-1 corpus) exit cleanly with
  `Cannot read PGN file` instead of a traceback.
- **PGN reader edge cases.** ChessBase-style glued move numbers (`1.e4`,
  `2...Nc6`) are accepted; an all-digit token with a leading zero (a
  nonstandard `00` castling attempt) fails loud instead of being silently
  swallowed as a move number and desyncing the replay; a stray trailing
  result token no longer yields a phantom empty game.

### Added

- A real full-length game mining fixture (`tests/data/opera_game.pgn`, the
  1858 Morphy Opera game, 33 plies, positions up to 32 men): mining it must
  finish fast (measured about 0.3 s pure Python; test bound 30 s) and its
  three mined puzzles — Bxd7+ winning the exchange, the Qb8+ queen-sacrifice
  mate in two, and Rd8# — are pinned exactly.

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
