# TDD — ChessPuzzleForge

**Status:** built (written retrospectively, 2026-08-03, against v2.2.0)
**Date:** 2026-08-03 · **PRD:** [PRD.md](PRD.md) ·
**Repo:** GreenPandaTech/ChessPuzzleForge (private)

> Derived by reading the code, not the README. Line references are to the tree
> at the time of writing; the module contracts below are what the functions
> actually do.

## Approach

Everything is built on one primitive — a pure-Python chess engine
(`engine.py`, ~750 lines, standard library only) that parses FEN, generates
*fully legal* moves, and answers one question exhaustively: *is there a move
that forces mate within N?* Around that sit four **producers** of puzzles (the
curated bank, `--fen` derivation, the PGN miner, the endgame synthesizer) and
exactly one **gate** they all pass through, `verifier.verify_puzzle`. A
producer's job is to find *candidates* cheaply; proving them is not its job and
it is not trusted to have done it. Nothing reaches stdout that has not been
re-proven immediately before printing.

The second design axis is boundedness. Every expensive search has an explicit
budget — a node cap on the fork proof, men-on-board and reply-count prefilters
in the miner, a sample cap in the synthesizer — and running out of budget
always means "not proven, so not reported", never "probably fine". This was
not aesthetic: v2.1.0 shipped an unbounded capture search that was measured
stalling 15+ minutes on one ordinary 32-man opening position.

There is no database, no server, no network and no persistent state. The
process reads argv (and optionally one file and one line of stdin), computes,
prints, and exits.

## Data model

No database, no migrations, no schema evolution. Three in-memory shapes carry
everything.

### `Puzzle` — `fen_bank.py`, a `TypedDict`

| Field | Type | Required | Meaning |
|---|---|---|---|
| `id` | `str` | yes | stable identifier; bank ids are hand-written, mined ids are `mined-g{game}-p{ply}-{kind}`, synthesized ids are `synth-{set}-m{n}-s{seed}-p{i}` |
| `fen` | `str` | yes | the position, side to move included |
| `goal` | `str` | yes | `mate_in_1` \| `mate_in_2` \| `mate_in_3` \| `win_material` |
| `solution` | `list[str]` | yes | accepted first moves in UCI. For mate-in-1 producers list **every** mating move; deeper goals list the one key move found |
| `san` | `str` | yes | display text only — e.g. `Qb8+ (then mate next move)`. Never parsed back |
| `theme` | `str` | yes | short human label |
| `threshold` | `float` | **no** | `win_material` only: minimum net pawns required |

`threshold` is `NotRequired`, so every consumer must treat it as absent —
`verify_solution` defaults it to `1.0`. This is the one field where a
"row predating the change" analogue exists: a `win_material` puzzle written
without a threshold verifies against 1.0 pawn, not against nothing.

The type is a `TypedDict` rather than a dataclass on purpose: puzzles are
serialised verbatim by `json.dumps(dict(puzzle), sort_keys=True)`, so the dict
*is* the wire format and there is no conversion layer to get out of step.

### `Board` — `engine.py`

`squares: list[str | None]` of length 64, index `rank*8 + file` (a1 = 0,
h8 = 63); uppercase = White, lowercase = Black; plus `turn`, `castling`,
`ep_square`, `halfmove`, `fullmove`. Documented as "immutable-ish": `push`
returns a **new** `Board` and never mutates the receiver, which is what makes
the recursive searches safe to write naively. It is not enforced — `__slots__`
prevents new attributes, not assignment to existing ones. Callers must not
mutate `squares` in place; nothing in the package does.

### `Move` / `Fork` / `Pin` / `Skewer` — frozen dataclasses

`Move(from_sq, to_sq, promotion=None, is_ep=False, is_castle=False)`, with
`uci()` as the canonical string form. Tactic records carry square *names*
(`str`), not indices, because they are for display and for the miner's
threshold arithmetic, not for further search.

## Interfaces

Module contracts, in dependency order. Everything below is re-exported from
`chesspuzzleforge/__init__.py`.

**`engine.py`** — no dependencies within the package.
- `Board.from_fen(fen) -> Board` / `Board.to_fen() -> str` — fail loud on a
  malformed FEN.
- `Board.legal_moves() -> list[Move]` — genuinely legal (castling rights and
  transit squares, en passant, promotions, self-check filtered).
- `Board.is_check(color=None) / is_checkmate() / is_stalemate() -> bool`.
- `Board.push(move) -> Board` — new position; raises on an empty from-square.
- `Board.ascii(perspective=WHITE) -> str` — see the [Design Brief](DESIGN_BRIEF.md).
- `move_to_san(board, move) -> str` / `parse_san(board, san) -> Move` /
  `move_from_uci(board, uci) -> Move` — all validate legality in `board`.
- `perft(board, depth) -> int` — the correctness harness, not used at runtime.
- `forced_mate_move(board, depth) -> str | None` — **the single source of
  mate truth in the project.** Exhaustive minimax over legal moves; `depth`
  counts moves by the side to move. Returns a UCI key move or `None`.

**`verifier.py`** — the gate.
- `verify_solution(puzzle, uci) -> (bool, str)` — is *this* move good enough for
  the puzzle's goal? Deliberately accepts any move that achieves the goal, not
  just the listed one (there can be several mating moves).
- `verify_puzzle(puzzle) -> (bool, str)` — **every** listed solution must pass.
  An empty `solution` fails.
- `net_material_gain(board, uci) -> float` — capture value minus the value of
  the piece left on the destination square, *if* the opponent has any legal
  recapture there. A two-ply model, and knowingly conservative: it does not see
  a follow-up win, so forks whose payoff needs another move are found by
  `find_forks` and then not emitted by the miner.

  The mate-goal branches take the cheap path first — the candidate alone is
  checked with `_move_forces_mate`; the exhaustive whole-position
  `forced_mate_move` runs only to *explain a wrong answer*. That asymmetry is
  what keeps re-verifying mined candidates affordable on full boards.

**`fen_bank.py`** — 10 curated puzzles (6 mate-in-1, 2 mate-in-2, 1 mate-in-3,
1 win-material) as module-level data. `all_puzzles()` / `puzzles_by_goal()` /
`get_puzzle(id)` all return **copies** (`p.copy()`), so a caller cannot mutate
the bank. `get_puzzle` raises `KeyError` on a miss.

**`generator.py`** — `derive_mate_in_1(fen)`, `make_puzzle_from_position(fen)`,
`generate_puzzle(goal=None, seed=None, validate=True, difficulty=None)`,
`render_puzzle(puzzle, reveal=False)`. `generate_puzzle` re-verifies before
returning and raises `AssertionError` if a *bank* puzzle fails — that is a
"the data shipped broken" condition, not user error, so it is loud and fatal.

**`tactics.py`** — `find_forks(board, min_gain=2.0, max_nodes=20_000)`,
`find_pins(board)`, `find_skewers(board)`. Forks are proven by a fail-soft
alpha-beta capture search (captures ordered by falling victim value) sharing
one node budget across the call; exceeding it raises internally and the
candidate is dropped as **unproven**. Pins and skewers are geometric only —
they are ray analysis, not proofs of material gain, and the miner never emits
them as puzzles.

**`pgn.py`** — `read_games(text) -> list[PgnGame]`. Tag pairs, glued or spaced
move numbers, brace and semicolon comments, NAGs, results, multiple games.
Parenthesised variations are skipped *and never validated*. `PgnError`
subclasses `ValueError` and names the game and line. Validates SAN **shape**
by regex only; legality is proven later by `parse_san` during replay.

**`miner.py`** — `mine_pgn(text, max_games, max_plies, progress)` /
`mine_games(games, ...)`. Per position: dedupe on the first four FEN fields
(move counters excluded), then prefilter, then search, then `_emit`, which
calls `verify_puzzle` and raises `AssertionError` on disagreement rather than
emitting. At most one puzzle per distinct position; mate beats fork.

**`synth.py`** — `parse_piece_set(spec)`, `synthesize_puzzles(piece_set,
mate_in=2, count=1, seed=None, max_tries=2000)`. Samples placements uniformly
with `random.Random(seed)`, rejects adjacent kings and positions where Black is
already in check, then requires mate at **exactly** `mate_in`: `_exact_mate_key`
runs the cheap shallower depths first and rejects on a hit, so a "mate in 2"
can never be a disguised mate in 1. Same `verify_puzzle` accept gate.

**`difficulty.py`** — `difficulty(puzzle) -> {score, band, factors}`.
`score = 8·depth + 0.4·branching + 0.3·rarity`, banded easy < 22 ≤ medium < 30 ≤ hard.
Pure, no clock, no randomness. Uncalibrated against human performance — see the
PRD's open questions.

**`export.py`** — `puzzle_to_json` (sorted keys, so byte-identical for identical
input) and `puzzle_to_pgn` (placeholder `Site`/`Date`/`White`/`Black`, so no
wall-clock and no identity in the output).

**`cli.py`** — `build_parser()`, `main(argv=None, reader=input) -> int`. The
`reader` injection is what makes interactive `--solve` testable without a tty.

### The budgets, in one place

| Constant | Value | Where | Why |
|---|---|---|---|
| `_SEARCH_NODE_BUDGET` | 20 000 | `tactics.py` | hard cap on the fork proof; exceeded ⇒ unproven ⇒ not reported |
| `_MATE_MATERIAL_MIN` | 5.0 | `miner.py` | skip deep mate search without at least a rook's worth (a 7th-rank pawn counts as a queen) |
| `_M2_SMALL_POSITION_MEN` | 8 | `miner.py` | full-width depth-2 search only at or below this |
| `_M2_FORCING_REPLY_MAX` | 4 | `miner.py` | above 8 men: checks-only scan, and only checks leaving ≤ 4 replies |
| `_M3_MAX_MEN` | 6 | `miner.py` | depth-3 search only in heavily simplified positions |
| `_MIN_FORK_THRESHOLD` | 1.0 | `miner.py` | a fork must prove at least a pawn under the recapture model |
| `DEFAULT_MAX_TRIES` | 2000 | `synth.py` | total samples across all requested puzzles |
| `_MAX_EXTRA_PIECES` | 3 | `synth.py` | white pieces between the kings |

## Trust boundaries

*The template's access-control section asks about RLS, security-definer
functions and grants to `anon`. **None of it applies**: there is no database,
no server, no auth and no multi-user surface. Inventing answers here would be
box-ticking, so the honest version of the section is the trust boundaries that
do exist.*

| Boundary | Input | Validation | Failure |
|---|---|---|---|
| argv | flags | `argparse` choices + explicit cross-flag checks in `main` | `parser.error` ⇒ exit 2 |
| `--fen` | arbitrary FEN | `Board.from_fen` | `ValueError` ⇒ `Invalid FEN: …`, exit 2 |
| `--mine` | a file | read as `utf-8-sig`; `read_games` regex + `parse_san` legality on replay | `PgnError`/`OSError`/`UnicodeDecodeError` ⇒ exit 2, naming game and line |
| `--solve` | one stdin line | `parse_san` then `move_from_uci`, both legality-checked | not a legal move ⇒ message, exit 2 |
| `--synth` | piece-set string | `parse_piece_set` | `ValueError` ⇒ exit 2 |
| **emission** | a candidate puzzle | `verify_puzzle` | bank: `AssertionError`; miner/synth: `AssertionError` — never a silent emit |

**The gate is not independent of discovery.** `verify_puzzle`,
`forced_mate_move` and the producers all sit on the same engine. The gate
catches pipeline defects — a mis-threaded FEN, an off-by-one in depth
accounting, the wrong SAN attached to the right move, a producer and prover
disagreeing — and it is worth having for exactly those. It cannot catch an
engine bug, because the engine is on both sides. The only independent evidence
in the repository is `tests/test_perft.py` (published reference node counts)
and `tests/test_with_chess.py` (`python-chess` as referee). Removing either
would leave the project's central claim resting on self-agreement.

## Migrations

None — there is no persistent store, so there is nothing to migrate and
nothing to roll forward. The closest analogue is the **2026-08-03 rename**,
which is a compatibility break for anyone importing the package:

| # | Does | Reversible? | Rollback |
|---|---|---|---|
| 1 | `git mv palamedes chesspuzzleforge`; rewrite imports, `prog=`, console script, `[tool.setuptools] packages`, `[tool.mypy] files`, badge/clone URLs, layout diagram | yes | `git revert` the rename commit |
| 2 | PGN export `Event` tag `Palamedes puzzle` → `ChessPuzzleForge puzzle` | yes | one-line revert; no test pinned the old string |

No compatibility shim (`palamedes/__init__.py` re-exporting the new package)
was added: the repository is private, unpublished, and has no external
importers, so a shim would be dead code preserving a name we are trying to
retire.

## Failure modes

| What breaks | Who notices | How we detect it | How we undo it |
|---|---|---|---|
| Engine move-gen bug | nobody, immediately — everything downstream agrees with it | perft counts diverge from published values; `python-chess` cross-check disagrees | fix the engine; both harnesses fail until it is right |
| Producer/gate disagreement (bad FEN threading, wrong depth) | the operator, at once | `_emit` / `_accept` raise `AssertionError` and the run dies | nothing was emitted; fix the producer |
| Bank data wrong | the operator | `--verify-all` exits 1; `tests/test_fen_bank.py` re-verifies every entry | correct the entry |
| Unbounded search (the v2.1.0 defect) | the user, as an apparent hang | `tests/test_perf.py` and the miner fixtures assert wall-clock bounds | node budget + prefilters; the regression is pinned |
| Malformed PGN misparsed as legal moves | the user, silently, in the worst case | `read_games` shape checks and `parse_san` legality; both fail loud with game and line | nothing emitted; exit 2 |
| Synthesis budget exhausted (e.g. `KNK`) | the user | `ValueError` ⇒ `Synthesis failed: …`, exit 2 | raise `--tries`, change seed, or use a set that can mate — never a downgraded goal |
| Non-determinism creeping in | CI | `tests/test_golden.py` digest tripwire; seeded determinism tests | revert the change |
| Optional referee absent | nobody | `pytest.importorskip("chess")` ⇒ 1 skipped, 223 passed | none needed; this is the supported state |

## Rollback

The process writes **nothing**: no files, no config, no cache, no network
calls. So there is no runtime state to roll back — stopping the tool is the
rollback, and it is instantaneous. The only durable artefacts a run can create
are the ones the *user's shell* creates by redirecting stdout, which the tool
neither knows about nor can undo.

For code: every change in this project is a `git revert` away, because there is
no schema and no deployed instance. The rename above is the only change that is
not internal to a single file, and it is a single commit. Nothing here is
irreversible.

## Test plan

289 tests with the referee installed, 223 without it. The ones that carry the
argument:

- **Positive** — `tests/test_fen_bank.py` re-verifies all 10 bank entries with
  the engine; `tests/test_miner.py` pins the exact puzzles mined from both
  fixtures, including all three from the 33-ply Opera game; `tests/test_synth.py`
  pins exactness and byte-identical determinism for a given seed.
- **Negative** — `tests/test_hostile.py` sweeps malformed input across every
  public entry point; `tests/test_pgn.py` pins fail-loud behaviour for
  unterminated tags, bad SAN, leading-zero move numbers and truncated
  movetext; `tests/test_synth.py` asserts that a candidate failing
  verification is **never** emitted.
- **Boundary** — `tests/test_perft.py` against published node counts (the
  strongest single test here: position-independent, and it fails for any
  move-generation bug regardless of where); `tests/test_perf.py` bounds
  wall-clock so the v2.1.0 hang cannot return; `tests/test_invariants.py`
  proves in a subprocess that importing the package never pulls in `chess`;
  `tests/test_version.py` keeps `__version__` and `pyproject` in lockstep.
- **Independent** — `tests/test_with_chess.py` cross-checks legal moves,
  checkmate detection, SAN round-tripping, mate solutions and absolute pins
  against `python-chess`, and skips cleanly when it is absent.

**Known gap:** the privacy property in the PRD — that no PGN tag data (player
names, event, date) reaches a mined puzzle or an exported PGN — is true by
construction but not asserted anywhere. `tests/test_export.py` pins the
placeholder `Date` and not the placeholder `White`/`Black`, and nothing asserts
the key set of a mined puzzle. A careless change could leak identity without
turning the suite red.

## Build order

Retrospective, since this is how it actually happened:

1. **v1.0.0** — engine (FEN, legal moves, check/mate/stalemate,
   `forced_mate_move`), bank, verifier, generator, CLI.
2. **v2.0.0** — perft harness, SAN parsing, mate-in-3, verified tactics,
   difficulty, `--solve`, export, ruff + `mypy --strict` + CI.
3. **v2.1.0** — PGN reader and mining pipeline.
4. **v2.1.1** — the boundedness round, forced by the measured 15-minute hang:
   node-budgeted fork proof, prefiltered depth-2 search, lazy failure hints.
5. **v2.2.0** — seeded endgame synthesis, plus the CLI empty-string
   fall-through fix.
6. **2026-08-03** — rename to ChessPuzzleForge; these documents.

## Open questions

- Should the miner's recall be measured against a known tactic set, so the
  "trades recall for speed" claim is a number rather than a description?
- Should the no-identity-in-output property be pinned by a test before it is
  claimed as a privacy feature anywhere user-facing?
