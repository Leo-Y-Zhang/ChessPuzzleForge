# PRD — ChessPuzzleForge

**Status:** built (written retrospectively, 2026-08-03, against v2.2.0)
**Date:** 2026-08-03 · **Repo:** GreenPandaTech/ChessPuzzleForge (private) ·
**Related:** [TDD](TDD.md), [App Flow](APP_FLOW.md), [Design Brief](DESIGN_BRIEF.md)

> This document was written after the code, from the code. Where it and the
> README disagree, the code wins and both get corrected.

## Problem

Chess puzzles circulate as position-plus-answer pairs — a FEN and a line of
text saying "mate in 2, Qh3". Nothing in that format is checkable. A
transcription slip, a wrong side-to-move, or a "mate in 2" that is really a
mate in 1 propagates silently into every tool built on top of the set, and the
person solving it just concludes they are bad at chess. The same problem
applies to a player's own games: to get puzzles out of them the usual route is
to upload the PGN to a website, which means handing over a file whose headers
name you, your opponent, your club and the date.

So: **a puzzle you cannot verify is a puzzle you cannot trust**, and the
convenient ways to get puzzles all require trusting someone else's answer key,
their server, or both.

## Who it is for

The author — a club-level player who wanted puzzles derived from their own PGN
files without uploading them anywhere, and who wanted a codebase where the
correctness claim is something you can *run* rather than something you have to
believe.

Second, and honestly the larger audience in practice: someone reading the
repository as a worked example of "prove it, do not assert it" — a from-scratch
chess engine whose move generator is pinned against published perft counts and
cross-checked against an independent implementation.

**This is a personal, educational tool.** It is not published to PyPI, has no
users beyond its author, and is not a competitor to any puzzle trainer. The
README says so and that must stay true.

## Success looks like

Each of these is a command someone else can run, not an opinion.

- [x] **Nothing reaches stdout unproven.** Every emission path — the curated
      bank, `--fen` derivation, `--mine`, `--synth` — passes through
      `verify_puzzle` before printing. `python -m chesspuzzleforge --verify-all`
      re-proves the whole bank and exits nonzero if any entry fails.
- [x] **Move generation is pinned independently.** `tests/test_perft.py` checks
      node counts against published reference values (startpos, Kiwipete and
      others); `tests/test_with_chess.py` cross-checks legal moves, checkmate
      detection, SAN and mate solutions against `python-chess`.
- [x] **The shipped tool has zero runtime dependencies.**
      `import chesspuzzleforge; 'chess' in sys.modules` is `False`, pinned by a
      subprocess test in `tests/test_invariants.py`. Core suite: **223 passed**
      with no third-party library installed; full suite **289 passed** with the
      referee present.
- [x] **A mate-in-N is exactly N.** The synthesizer accepts a position only when
      the prover finds mate at depth N *and* fails at every shallower depth.
- [x] **Bad input fails loud.** Malformed PGN names the game and the move and
      exits 2; an unsupported piece set exits 2. Neither ever degrades into a
      quietly wrong answer.
- [x] **Deterministic.** The same `--seed` produces byte-identical output;
      `tests/test_golden.py` is a digest tripwire over the bank export.
- [x] **Real games mine in about a second.** The 33-ply Opera game fixture
      (positions up to 32 men) mines end to end in roughly 0.3 s of pure Python.

## Requirements

**Must**

- Every puzzle re-proven by the engine immediately before emission.
- Pure standard library at runtime; the optional `python-chess` referee is
  dev/test-only and the suite skips cleanly without it.
- Offline: no network calls, no telemetry, no account.
- Deterministic given a seed.
- Fail loud on malformed input; never emit a downgraded or guessed answer.
- Bounded work: every search runs under an explicit node or sample budget.

**Should**

- Mine puzzles from a user-supplied PGN corpus.
- Synthesize fresh endgame puzzles from a piece set with no input file at all.
- Deterministic JSON and PGN export so output composes with other tools.
- A difficulty score that is at least *reproducible*, even if uncalibrated.

**Won't (this time)**

- Playing strength or a general search. The forced-mate solver is exhaustive
  and only sane to depth 3.
- Tablebases, an opening book, or an evaluation function beyond material.
- A GUI, a web UI, or any persistent store.
- Publication to PyPI.

## Explicitly out of scope

- **Being a strong engine.** `forced_mate_move` is a small exhaustive minimax.
  It is correct at depths 1–3 and useless beyond that; nothing in the project
  pretends otherwise.
- **Complete tactic recall.** The miner's prefilters trade recall for bounded
  time by design: full-width depth-2 search only at ≤ 8 men, a checks-only
  scan above that, depth 3 only at ≤ 6 men, forks only when a node-budgeted
  capture search *proves* the gain. Tactics present in a game will be missed.
  Soundness is the promise; recall is not, and is not measured.
- **Non-mainline PGN.** Parenthesised variations are skipped and never
  validated, so every mined puzzle comes from a position that actually
  occurred.
- **Pawns in synthesis.** They would need placement and promotion rules for no
  mate coverage gain at depths 1–3.
- **Storing anything.** The tool writes no files. Output goes to stdout; if the
  user redirects it, that is their shell's business.

## Safety and privacy

- **Personal data it touches:** only whatever is in a PGN file the user points
  `--mine` at. PGN tag pairs routinely carry both players' names, the event,
  the club and the date.
- **What propagates:** nothing identifying. A mined puzzle carries only
  `id` / `fen` / `goal` / `solution` / `san` / `theme` (+ `threshold`); the
  reader consumes tag pairs but only ever reads `FEN` back out, and ids are
  built from the game number and ply. Exported PGN hard-codes
  `[White "?"] [Black "?"] [Site "?"] [Date "????.??.??"]`. So a mined puzzle
  cannot be traced back to the players by inspecting it.
  **Gap, stated honestly:** this property is true by construction but only
  partly pinned by tests — `tests/test_export.py` asserts the placeholder
  `Date` but not the placeholder `White`/`Black`, and no test asserts that a
  mined puzzle carries no tag-derived keys. It would survive a careless change
  unnoticed.
- **Who can see it:** only the person at the terminal. There is no server, no
  account and no upload, so access revocation does not apply — there is no
  access to revoke. The equivalent question is what happens to the user's PGN:
  it is read once, never written, never copied, never retained.
- **Worst outcome if this is wrong:** the tool confidently states a mate that
  is not a mate. Someone trains against a false answer and, worse, stops
  trusting the one property the project exists to provide.

  The mitigation is the `verify_puzzle` gate on every emission — but that gate
  is **not independent of discovery**: both call the same `forced_mate_move`.
  It catches pipeline bugs (a mis-threaded FEN, an off-by-one depth, the wrong
  SAN attached to the right move) and it would catch a divergence between
  discovery and proof. It cannot catch a bug *inside* the engine, because the
  engine is on both sides of the check. The only genuinely independent evidence
  is the perft harness and the `python-chess` cross-check, and that is why both
  exist and why neither may be dropped for convenience.

## Open questions

None blocking, but two are real and unanswered:

1. **Recall is unmeasured.** We claim soundness and explicitly disclaim recall,
   but there is no benchmark saying what fraction of a known tactic set the
   miner finds. Without one, "the prefilters trade recall for speed" is a
   description, not a measurement.
2. **Difficulty is uncalibrated.** `score = 8·depth + 0.4·branching +
   0.3·rarity`, with band cutoffs at 22 and 30, is a hand-picked formula with
   hand-picked thresholds. It is deterministic and auditable, which is all it
   currently claims. Whether it correlates with how hard a human finds the
   puzzle is unknown, and the docs should not imply otherwise.

## Not doing / rejected alternatives

- **Use `python-chess` for move generation.** Rejected. It would have removed
  the entire point (a from-scratch engine) *and* destroyed the independence of
  the referee — you cannot cross-check a library against itself. It is kept as
  a dev/test-only second opinion, which is worth far more than the code it
  would have saved.
- **Ship a downloaded puzzle database.** Rejected. An imported answer key is
  exactly the thing the project exists to avoid; it also imports someone else's
  licensing and megabytes of data into a zero-dependency repo.
- **Call an external engine (Stockfish over UCI) to verify.** Rejected for now:
  a binary dependency, process management and a platform matrix, in exchange
  for depth the project does not need at mate-in-1-to-3. Parked as an explicit
  opt-in V3 idea, kept offline if it ever happens.
- **A SQLite puzzle store.** Rejected for now. JSON lines on stdout compose
  with `jq`, `sort` and `>` for free and keep the dependency count at zero.
  Listed on the roadmap, not built.
- **Full-width mate search everywhere in the miner.** Rejected on evidence, not
  taste: v2.1.0 was measured stalling **15+ minutes** on a single ordinary
  32-man opening position. Replaced in v2.1.1 by prefilters plus a hard node
  budget, with the recall loss written down and pinned by a test. Bounded and
  honest beat complete and hung.
- **A colour or curses interface.** Rejected — see the
  [Design Brief](DESIGN_BRIEF.md). Plain ASCII on stdout stays pipeable,
  screen-reader-friendly and diffable in CI.
