# ChessPuzzleForge — technical design

Derived by reading the code at v2.2.0, not the README. The module contracts
below are what the functions actually do. Requirements: [PRD.md](PRD.md).

## Nothing is printed that has not just been re-proven

Everything is built on a pure-Python chess engine — `engine.py`, about 750 lines,
standard library only — that parses FEN, generates *fully legal* moves, and
answers one question exhaustively: is there a move that forces mate within N?

Around it sit four **producers** of puzzles (the curated bank, `--fen`
derivation, the PGN miner, the endgame synthesizer) and exactly one **gate** they
all pass through, `verifier.verify_puzzle`. A producer's job is to find
*candidates* cheaply. Proving them is not its job, and it is not trusted to have
done it. Nothing reaches stdout that has not been re-proven immediately before
printing.

There is no database, no server, no network and no persistent state. The process
reads argv — plus optionally one file and one line of stdin — computes, prints,
and exits.

## Boundedness, forced by a 15-minute hang

The second design axis is not aesthetic. v2.1.0 shipped an unbounded capture
search that was measured stalling **15+ minutes** on one ordinary 32-man opening
position.

So every expensive search now has an explicit budget, and running out of budget
always means "not proven, therefore not reported" — never "probably fine".

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

## The three shapes

No database, no migrations, no schema evolution. Three in-memory shapes carry
everything.

**`Puzzle`** — `fen_bank.py`, a `TypedDict`.

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
`verify_solution` defaults it to `1.0`. This is the one field with a
"row predating the change" analogue: a `win_material` puzzle written without a
threshold verifies against 1.0 pawn, not against nothing.

The type is a `TypedDict` rather than a dataclass on purpose. Puzzles are
serialised verbatim by `json.dumps(dict(puzzle), sort_keys=True)`, so the dict
*is* the wire format and there is no conversion layer to get out of step.

**`Board`** — `engine.py`. `squares: list[str | None]` of length 64, indexed
`rank*8 + file` (a1 = 0, h8 = 63), uppercase for White and lowercase for Black,
plus `turn`, `castling`, `ep_square`, `halfmove`, `fullmove`. Documented as
"immutable-ish": `push` returns a **new** `Board` and never mutates the receiver,
which is what makes the recursive searches safe to write naively. It is not
enforced — `__slots__` prevents new attributes, not assignment to existing ones —
so callers must not mutate `squares` in place. Nothing in the package does.

**`Move` / `Fork` / `Pin` / `Skewer`** — frozen dataclasses.
`Move(from_sq, to_sq, promotion=None, is_ep=False, is_castle=False)`, with
`uci()` as the canonical string form. Tactic records carry square *names* rather
than indices, because they are for display and for the miner's threshold
arithmetic, not for further search.

## Module contracts

In dependency order. Everything below is re-exported from
`chesspuzzleforge/__init__.py`.

**`engine.py`** has no dependencies within the package.
`Board.from_fen(fen) -> Board` and `Board.to_fen() -> str` fail loud on a
malformed FEN. `Board.legal_moves() -> list[Move]` is genuinely legal — castling
rights and transit squares, en passant, promotions, self-check filtered.
`Board.is_check(color=None)`, `is_checkmate()` and `is_stalemate()` return
`bool`. `Board.push(move) -> Board` returns a new position and raises on an empty
from-square. `Board.ascii(perspective=WHITE) -> str` is covered in the
[Design Brief](DESIGN_BRIEF.md). `move_to_san`, `parse_san` and `move_from_uci`
all validate legality in `board`. `perft(board, depth) -> int` is the correctness
harness and is not used at runtime. And `forced_mate_move(board, depth) ->
str | None` is **the single source of mate truth in the project** — an
exhaustive minimax over legal moves, with `depth` counting moves by the side to
move, returning a UCI key move or `None`.

**`verifier.py`** is the gate. `verify_solution(puzzle, uci) -> (bool, str)` asks
whether *this* move is good enough for the puzzle's goal, and deliberately
accepts any move that achieves the goal rather than only the listed one, since
there can be several mating moves. `verify_puzzle(puzzle) -> (bool, str)`
requires **every** listed solution to pass, and an empty `solution` fails.
`net_material_gain(board, uci) -> float` is capture value minus the value of the
piece left on the destination square, *if* the opponent has any legal recapture
there — a two-ply model, knowingly conservative, which does not see a follow-up
win, so forks whose payoff needs another move are found by `find_forks` and then
not emitted by the miner.

One asymmetry inside the gate matters for cost: the mate-goal branches take the
cheap path first, checking the candidate alone with `_move_forces_mate`, and run
the exhaustive whole-position `forced_mate_move` only to *explain a wrong
answer*. That is what keeps re-verifying mined candidates affordable on full
boards.

**`fen_bank.py`** holds 10 curated puzzles — six mate-in-1, two mate-in-2, one
mate-in-3, one win-material — as module-level data. `all_puzzles()`,
`puzzles_by_goal()` and `get_puzzle(id)` all return **copies** (`p.copy()`), so a
caller cannot mutate the bank, and `get_puzzle` raises `KeyError` on a miss.

**`generator.py`** provides `derive_mate_in_1(fen)`,
`make_puzzle_from_position(fen)`,
`generate_puzzle(goal=None, seed=None, validate=True, difficulty=None) -> Puzzle`
and `render_puzzle(puzzle, reveal=False)`. `generate_puzzle` re-verifies before
returning and raises `AssertionError` if a *bank* puzzle fails — that is a "the
data shipped broken" condition rather than user error, so it is loud and fatal.

**`tactics.py`** provides `find_forks(board, min_gain=2.0, max_nodes=20_000)`,
`find_pins(board)` and `find_skewers(board)`. Forks are proven by a fail-soft
alpha-beta capture search, captures ordered by falling victim value, sharing one
node budget across the call; exceeding it raises internally and the candidate is
dropped as **unproven**. Pins and skewers are geometric only — ray analysis, not
proofs of material gain — and the miner never emits them as puzzles.

**`pgn.py`** provides `read_games(text) -> list[PgnGame]`, handling tag pairs,
glued or spaced move numbers, brace and semicolon comments, NAGs, results and
multiple games. Parenthesised variations are skipped *and never validated*.
`PgnError` subclasses `ValueError` and names the game and line. SAN **shape** is
validated by regex only; legality is proven later by `parse_san` during replay.

**`miner.py`** provides `mine_pgn(text, max_games, max_plies, progress)` and
`mine_games(games, ...)`. Per position: dedupe on the first four FEN fields, move
counters excluded, then prefilter, then search, then `_emit`, which calls
`verify_puzzle` and raises `AssertionError` on disagreement rather than emitting.
At most one puzzle per distinct position; mate beats fork.

**`synth.py`** provides `parse_piece_set(spec)` and `synthesize_puzzles(...)`. It
samples placements uniformly with `random.Random(seed)`, rejects adjacent kings
and positions where Black is already in check, then requires mate at **exactly**
`mate_in`: `_exact_mate_key` runs the cheap shallower depths first and rejects on
a hit, so a "mate in 2" can never be a disguised mate in 1. Same `verify_puzzle`
accept gate.

**`difficulty.py`** provides `difficulty(puzzle) -> {score, band, factors}`, with
`score = 8·depth + 0.4·branching + 0.3·rarity` banded easy < 22 ≤ medium < 30 ≤
hard. Pure, no clock, no randomness, and uncalibrated against human performance.

**`export.py`** provides `puzzle_to_json` (sorted keys, so byte-identical for
identical input) and `puzzle_to_pgn` (placeholder `Site`/`Date`/`White`/`Black`,
so no wall-clock and no identity in the output).

**`cli.py`** provides `build_parser()` and `main(argv=None, reader=input) -> int`.
The `reader` injection is what makes interactive `--solve` testable without a
tty.

## Trust boundaries

There is no database, no server, no auth and no multi-user surface, so the usual
access-control questions have nothing to attach to. What does exist is six
boundaries where untrusted input enters.

| Boundary | Input | Validation | Failure |
|---|---|---|---|
| argv | flags | `argparse` choices + explicit cross-flag checks in `main` | `parser.error` ⇒ exit 2 |
| `--fen` | arbitrary FEN | `Board.from_fen` | `ValueError` ⇒ `Invalid FEN: …`, exit 2 |
| `--mine` | a file | read as `utf-8-sig`; `read_games` regex + `parse_san` legality on replay | `PgnError`/`OSError`/`UnicodeDecodeError` ⇒ exit 2, naming game and line |
| `--solve` | one stdin line | `parse_san` then `move_from_uci`, both legality-checked | not a legal move ⇒ message, exit 2 |
| `--synth` | piece-set string | `parse_piece_set` | `ValueError` ⇒ exit 2 |
| **emission** | a candidate puzzle | `verify_puzzle` | bank: `AssertionError`; miner/synth: `AssertionError` — never a silent emit |

That last row is the important one, and it is weaker than it looks.
`verify_puzzle`, `forced_mate_move` and the producers all sit on the same engine.
The gate catches pipeline defects — a mis-threaded FEN, an off-by-one in depth
accounting, the wrong SAN attached to the right move, a producer and prover
disagreeing — and it is worth having for exactly those. It cannot catch an engine
bug, because the engine is on both sides. The only independent evidence in the
repository is `tests/test_perft.py`, using published reference node counts, and
`tests/test_with_chess.py`, using `python-chess` as referee. Removing either
would leave the project's central claim resting on self-agreement.

## What goes wrong, and what the user sees

| What breaks | Who notices | How we detect it | How we undo it |
|---|---|---|---|
| Engine move-gen bug | nobody, immediately — everything downstream agrees with it | perft counts diverge from published values; `python-chess` cross-check disagrees | fix the engine; both harnesses fail until it is right |
| Producer/gate disagreement (bad FEN threading, wrong depth) | the operator, at once | `_emit` / `_accept` raise `AssertionError` and the run dies | nothing was emitted; fix the producer |
| Bank data wrong | the operator | `--verify-all` exits 1; `tests/test_fen_bank.py` re-verifies every entry | correct the entry |
| Unbounded search (the v2.1.0 defect) | the user, as an apparent hang | `tests/test_perf.py` and the miner fixtures assert wall-clock bounds | node budget + prefilters; the regression is pinned |
| Malformed PGN misparsed as legal moves | the user, silently, in the worst case | `read_games` shape checks and `parse_san` legality; both fail loud with game and line | nothing emitted; exit 2 |
| Synthesis budget exhausted (e.g. `KNK`) | the user | `ValueError` ⇒ `Synthesis failed: …`, exit 2 | raise `--tries`, change seed, or use a set that can mate — never a downgraded goal |
| Non-determinism creeping in | CI | `tests/test_golden.py` digest tripwire; seeded determinism tests | revert the change |
| Optional referee absent | nobody | `pytest.importorskip("chess")` ⇒ 1 skipped, 227 passed | none needed; this is the supported state |

## The rename is the only non-internal change

There is no persistent store, so nothing migrates and nothing rolls forward. The
closest analogue is the 2026-08-03 rename, which is a compatibility break for
anyone importing the package.

| # | Does | Reversible? | Rollback |
|---|---|---|---|
| 1 | `git mv palamedes chesspuzzleforge`; rewrite imports, `prog=`, console script, `[tool.setuptools] packages`, `[tool.mypy] files`, badge/clone URLs, layout diagram | yes | `git revert` the rename commit |
| 2 | PGN export `Event` tag `Palamedes puzzle` → `ChessPuzzleForge puzzle` | yes | one-line revert; no test pinned the old string |

No compatibility shim — a `palamedes/__init__.py` re-exporting the new package —
was added. The repository is private, unpublished and has no external importers,
so a shim would be dead code preserving a name we are trying to retire.

## Undoing a release, and why there is nothing else to undo

The process writes **nothing**: no files, no config, no cache, no network calls.
There is no runtime state to roll back, so stopping the tool is the rollback and
it is instantaneous. The only durable artefacts a run can create are the ones the
*user's shell* creates by redirecting stdout, which the tool neither knows about
nor can undo.

For code, every change is a `git revert` away, because there is no schema and no
deployed instance. The rename above is the only change not internal to a single
file, and it is a single commit.

## The suite

293 tests with the referee installed, 227 without it. The ones carrying the
argument:

**Positive.** `tests/test_fen_bank.py` re-verifies all 10 bank entries with the
engine. `tests/test_miner.py` pins the exact puzzles mined from both fixtures,
including all three from the 33-ply Opera game. `tests/test_synth.py` pins
exactness and byte-identical determinism for a given seed.

**Negative.** `tests/test_hostile.py` sweeps malformed input across every public
entry point. `tests/test_pgn.py` pins fail-loud behaviour for unterminated tags,
bad SAN, leading-zero move numbers and truncated movetext. `tests/test_synth.py`
asserts that a candidate failing verification is **never** emitted.

**Boundary.** `tests/test_perft.py` against published node counts — the strongest
single test here, because it is position-independent and fails for any
move-generation bug regardless of where. `tests/test_perf.py` bounds wall-clock
so the v2.1.0 hang cannot return. `tests/test_invariants.py` proves in a
subprocess that importing the package never pulls in `chess`.
`tests/test_version.py` keeps `__version__` and `pyproject` in lockstep.

**Independent.** `tests/test_with_chess.py` cross-checks legal moves, checkmate
detection, SAN round-tripping, mate solutions and absolute pins against
`python-chess`, and skips cleanly when it is absent.

One known gap. The privacy property in the PRD — that no PGN tag data reaches a
mined puzzle or an exported PGN — is true by construction but not asserted
anywhere. `tests/test_export.py` pins the placeholder `Date` and not the
placeholder `White`/`Black`, and nothing asserts the key set of a mined puzzle. A
careless change could leak identity without turning the suite red, and that
should be pinned before the property is claimed anywhere user-facing.

## How it arrived, release by release

**v1.0.0** — engine (FEN, legal moves, check/mate/stalemate,
`forced_mate_move`), bank, verifier, generator, CLI.

**v2.0.0** — perft harness, SAN parsing, mate-in-3, verified tactics, difficulty,
`--solve`, export, ruff plus `mypy --strict` plus CI.

**v2.1.0** — PGN reader and mining pipeline.

**v2.1.1** — the boundedness round, forced by the measured 15-minute hang:
node-budgeted fork proof, prefiltered depth-2 search, lazy failure hints.

**v2.2.0** — seeded endgame synthesis, plus the CLI empty-string fall-through
fix.

**2026-08-03** — rename to ChessPuzzleForge, and these documents.
