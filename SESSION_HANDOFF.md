# Session handoff - Palamedes

## PROJECT STATUS (2026-07-31) - v2.2.0 endgame synthesis round COMPLETE, committed locally

Feature round (workflow: implement -> adversarial review -> finalize). All commits
local on main, NOT pushed - the orchestrator pushes after its verification sweep.

- NEW `palamedes/synth.py`: seeded endgame synthesis. Uniform sampling from a
  bounded piece set (white K + 1-3 of Q/R/B/N + bare black king, White to move)
  via random.Random(seed); illegal placements rejected (adjacent kings, defender
  in check); a sample is kept only when forced_mate_move proves mate in EXACTLY
  the requested N (present at N, absent at every shallower depth); every accepted
  candidate re-proven through verify_puzzle before emission (verifier disagreement
  raises, never emits). Output mirrors the miner (m1 lists every mating move).
- CLI: `--synth PIECES` composes with --goal mate_in_1|2|3 (default 2), --seed,
  --reveal, --solve; --count N emits JSON lines like --mine; --tries bounds the
  budget (default 2000). parse_piece_set/synthesize_puzzle/synthesize_puzzles
  re-exported.
- Adversarial review: no blockers/majors; 3 minors -> 2 fixed, 1 rejected:
  (1) FIXED empty-string fall-through: --synth "" / --mine "" / --fen "" used to
  truthiness-skip their branch and print a bank puzzle exit 0; all three now take
  their own error path, exit 2 (regression tests added in test_cli_synth/
  test_cli_mine/test_cli).
  (2) FIXED --count silently dropping --solve/--reveal: now a parser error.
  (3) REJECTED docs-only finding: the "p well above 1%" phrasing lived only in the
  implementer report, not in any committed file (repo comment says
  "astronomically unlikely", which holds: reviewer measured p ~ 1.03%, flake
  probability ~ e^-206).
- Docs: CHANGELOG 2.2.0 (all numbers run-verified this session), README v2.2
  section + "Synthesizing fresh endgames" live transcript + counts/layout/scope
  updated. Version 2.2.0 in lockstep (pyproject + __init__ + test_version).
- Gates at head (run this session): full suite 289 passed, core-only
  (--ignore=tests/test_with_chess.py) 223 passed, ruff clean, mypy --strict clean
  (13 files). Timings measured: --synth KRK --seed 7 ~1.5s end-to-end; KQK
  --count 2 --seed 9 ~0.4s; KRRK m3 --seed 0 ~0.6s.

Exact next step: orchestrator verification sweep, then push main (PRIVATE repo,
GreenPandaTech noreply identity).

---

## PROJECT STATUS (2026-07-30, later) - v2.1.1 review-fix round COMPLETE, committed locally

Confirmed review finding fixed: the v2.1.0 miner effectively hung on REAL games
(find_forks ran an unbounded all-captures negamax; one ordinary 32-man opening
position took 15+ minutes). All local commits on main, NOT pushed:

- `tactics.py`: fork proof is now fail-soft alpha-beta (captures ordered by falling
  victim value) under a hard node budget (`find_forks(..., max_nodes=20000)`, shared
  per call). Full-window root values are IDENTICAL to the old negamax (pinned tests
  unchanged); the 32-man position now takes ~1 ms; budget-exhausted candidates are
  unproven -> not reported (soundness over recall).
- `miner.py`: depth-2 mate search above 8 men is a bounded checks-only scan
  (checking key moves leaving <= 4 replies, each reply confirmed by a mate-in-1
  scan); full-width forced_mate_move still runs at <= 8 men (quiet keys). The
  recall trade is pinned by a test (11-men quiet-key m2 is real but not emitted).
- `verifier.py`: mate-goal failure hint computed lazily (success path never runs the
  whole-position search); messages unchanged.
- `cli.py`: --mine reads utf-8-sig, catches UnicodeDecodeError -> clean exit 2.
- `pgn.py`: glued move numbers (1.e4 / 2...Nc6) accepted; zero-led digit tokens
  (nonstandard 00 castling) fail loud instead of silently desyncing; stray trailing
  result no longer yields a phantom empty game.
- NEW fixture `tests/data/opera_game.pgn` (Morphy 1858, 33 plies, 32-man positions):
  mines in ~0.3 s, 3 puzzles pinned exactly (Bxd7+ exchange win, Qb8+ mate-in-2
  queen sac, Rd8#). README/CHANGELOG updated honestly; version 2.1.1 in lockstep.
- Gates at head: full suite 250 passed, core-only 184 passed, ruff clean,
  mypy --strict clean.

Exact next step: user review, then push main (PRIVATE repo, GreenPandaTech noreply).

---

## PROJECT STATUS (2026-07-30) - v2.1.0 PGN mining round COMPLETE, committed locally

v2.0.0 shipped earlier (merged + tagged; the v2 program notes below are HISTORICAL).
This round added **v2.1.0 - PGN corpus mining** on main, in local commits that are
**NOT yet pushed** (the round's instructions were commit-only):

- `palamedes/pgn.py` - stdlib mainline PGN reader, fail-loud (PgnError names game+line).
- `palamedes/miner.py` - mine_pgn/mine_games: replay via parse_san, cheap prefilters
  (checks available / mating material / men on board / forcing-reply counts) before the
  expensive searches (mate-in-1 scan, forced_mate_move depths 2-3, find_forks), dedupe
  by position, EVERY candidate re-verified through verify_puzzle before emission.
- CLI `--mine games.pgn` + `--max-games` / `--max-plies`; JSON lines out, progress to
  stderr. Fixture `tests/data/mined_games.pgn` (castling + promotion in movetext) mines
  8 exactly-pinned puzzles in ~2s.
- Small fixes: render_puzzle mate_in_3 label; README CI-matrix claim corrected to the
  single-3.13 truth. CHANGELOG 2.1.0; versions in lockstep.
- Gates at head: full suite 237 passed (`.venv/Scripts/python.exe -m pytest -q`),
  core-only 171 passed, ruff clean, mypy --strict clean.

Exact next step: user review, then push main (PRIVATE repo, GreenPandaTech noreply).

---

HISTORICAL (v2.0.0 "to the max" program notes, kept for context; counts are stale):

## THE HARD GATE (correctness + honesty) - the review lens
Engine-verified correctness FOREVER (never an illegal move / unverified puzzle / a
"mate in N" that is not mate; move gen pinned by PERFT; every generated tactic
re-verified by the engine; the optional python-chess cross-check keeps agreeing). ZERO
runtime deps (stdlib-only core; python-chess dev/test-only + importorskip). Deterministic
/reproducible (same --seed -> same puzzle; no wall-clock / unseeded randomness in results;
golden digest). Offline (no network). Fail-loud (invalid FEN / illegal move / malformed
input -> ValueError, never a silent guess or traceback). Additive/back-compat (v1 API +
CLI unchanged; additions opt-in).

## v1 core API (all pure stdlib)
engine.py: Board (FEN parse/emit, ASCII, legal move gen incl castling/en-passant/
promotion, check/checkmate/stalemate), forced_mate_move (exhaustive mate-in-1/2), plus
square/file_of/rank_of/square_name/parse_square helpers. fen_bank.py: 9 curated verified
puzzles. verifier.py: mate-in-1/2 + win-material (2-ply). generator.py: derive_mate_in_1,
generate_puzzle, rendering. cli.py: argparse (--goal, --seed, --reveal, --fen, --list,
--verify-all). Tests: test_engine/fen_bank/verifier/generator/cli (stdlib) +
test_with_chess.py (importorskip chess referee).

## Build order (spec steps) - status
- [x] Step 0 - Tooling: pyproject (ruff E/F/W/I/UP/B/SIM + mypy --strict) + CI lint/type + baseline test
- [x] Step 1 - Perft correctness harness (perft(board,depth) + known-value reference table)
- [x] Step 2 - SAN parse (parse_san w/ full disambiguation; round-trip; cross-check chess)
- [x] Step 3 - Mate-in-3 search (forced_mate_in_n up to 3, perf-bounded, verified)
- [x] Step 4 - Verified motif: forks (find_forks, engine-verified double attack + material gain)
- [x] Step 5 - Verified motifs: pins & skewers (find_pins/find_skewers, geometric + engine-verified)
- [x] Step 6 - Difficulty scoring + --difficulty filter (pure, deterministic)
- [x] Step 7 - Interactive solve mode + SAN input in the CLI (additive)
- [x] Step 8 - Export (PGN + JSON) + golden digest + hostile-input sweep + perf sanity
- [ ] Step 9 - Docs + version 2.0.0 + final adversarial 3-lens review + merge --no-ff + tag v2.0.0

## Exact next step
Step 9 - Docs + version 2.0.0 + final adversarial 3-lens review + merge --no-ff + tag (RELEASE, LAST
step). (a) DOCS: rewrite README for the v2 story (perft harness / SAN parse / mate-in-3 / VERIFIED
forks / pins & skewers / difficulty + --difficulty / --solve mode / PGN+JSON export) - KEEP the
"PROVES every answer" + zero-runtime-dep framing; update the test count to 201; FIX the Python badge
(3.9 -> 3.11) + the Setup note (requires-python was bumped to 3.11 in Step 0); add CHANGELOG.md
(v2.0.0 entry). Bump kineo... NO: palamedes/__init__ __version__ 1.0.0 -> 2.0.0 AND pyproject version
-> 2.0.0 in LOCKSTEP + a test asserting they match (parse pyproject with a regex, no tomllib). (b)
FINAL ADVERSARIAL 3-LENS REVIEW (a Workflow) of the WHOLE v2: correctness (engine perft-pinned; every
tactic/mate PROVEN by the engine + cross-checked vs python-chess; never an illegal move or a false
tactic; parse_san/move_to_san agree), robustness (every public entry fails loud on hostile input),
determinism+purity (no wall-clock/random in any result or export; the golden reflects the real
pipeline; import palamedes / import palamedes.cli need NO chess; zero runtime deps). Reproduce + fix
every real finding with a regression test; re-run the gate. (c) MERGE + TAG: git checkout main ->
git merge origin/main (reconcile any parallel proprietary-licence commit, KEEP proprietary; reset
--hard DENIED) -> git merge --no-ff feature/to-the-max -> gate green on the merge -> push main
(PRIVATE, allowed) -> tag v2.0.0 annotated (gh api to move a tag if needed) -> delete feature branch
(local+remote) -> verify CI green -> update memory (project_repo_max_upgrades: Palamedes v2.0.0 DONE)
+ handoff -> START Mentor (repo #16). NOTE: README currently claims Python 3.9+ but requires-python
is now 3.11 (Step 0) - fix the badge + Setup note here for honesty.

DONE Step 8 (2026-07-12): NEW palamedes/export.py puzzle_to_json(puzzle) (DETERMINISTIC json.dumps
sort_keys) + puzzle_to_pgn(puzzle) (minimal VALID PGN: Event/Site/Date "????.??.??" [NO wall-clock] /
Round/White/Black/Result/SetUp "1"/FEN/PuzzleGoal tags + the key move in SAN via move_to_san;
move_from_uci validates legality). Fail-loud (ValueError) on non-str fen/goal or a missing solution.
Re-exported puzzle_to_json/puzzle_to_pgn. VERIFIED all 10 bank PGNs PARSE with python-chess (FEN
round-trips, exactly 1 move each). NEW tests: test_export.py (json deterministic + sorted keys; pgn
tags + key move + placeholder date; fail-loud); test_golden.py pins sha256 of the whole-bank sorted
puzzle_to_json = 0a4ca774cc89612915ea19ec41a2eeb2804777dbdb15b844b3987eaa21e5e6cf (regenerate ONLY on
an intentional change) + repeat-stable; test_hostile.py sweep (from_fen rejects 5 bad FENs incl
7-ranks / rank-sum-9 / bad-piece / bad-side; move_from_uci malformed + illegal; parse_san garbage /
empty / O-O-O-O; difficulty unknown goal; generate_puzzle impossible; export malformed -> all
ValueError; find_forks/pins/skewers on bare kings -> []); test_perf.py perft(startpos,3)==8902 under
10s. Full suite 182 -> 201 in ~3.7s, ruff + mypy strict clean (10 files).

DONE Step 7 (2026-07-12): cli.py interactive --solve mode + SAN input (additive; v1 CLI unchanged).
main(argv, reader=input) now takes an INJECTABLE reader (testable without real stdin). NEW
_read_move(board, raw) accepts SAN (parse_san) OR UCI (move_from_uci) - tries parse_san first then
falls back; None if neither parses. NEW _cmd_solve(puzzle, reader): prints the puzzle solution-
HIDDEN, reads one move, verifies via verify_solution(puzzle, move.uci()), prints Correct! / Not the
solution + a HINT (the from-square of the listed key move); an illegal/garbage move -> clean stderr
message + exit 2 (no traceback); no move (EOF) -> exit 1; correct/incorrect both -> exit 0. --solve
flag added; composes with --fen or --seed/--goal/--difficulty. TDD test_cli.py +4 (injected reader
lambda): correct SAN Ra8 -> exit 0 + 'correct'; correct UCI a1a8 -> exit 0; wrong-legal Ra7 -> exit
0 + 'not the solution' + 'hint'; illegal Qz9 -> exit 2 + 'legal' message. Full suite 178 -> 182,
ruff + mypy strict clean (9 files).

DONE Step 6 (2026-07-12): NEW palamedes/difficulty.py difficulty(puzzle) -> {score, band, factors}
(PURE, DETERMINISTIC - no wall-clock / random; param typed Mapping[str,object] so a plain dict or a
Puzzle both work + runtime isinstance guards). Formula (documented): score = 8*depth +
0.4*branching + 0.3*rarity, where depth = mate_in_N -> N / win_material -> 1, branching =
len(legal_moves at the key FEN), rarity = branching - number of listed solving moves. Bands:
easy < 22, medium < 30, else hard (calibrated on the bank -> 4 easy / 3 medium / 3 hard; the
formula PRESERVES depth ordering: every mate_in_1 < every mate_in_2 < the mate_in_3). Fail-loud:
non-string fen/goal or unknown goal -> ValueError. generate_puzzle(goal, seed, validate,
difficulty=None) filters the pool by band, and no match -> ValueError with a clear message. cli
--difficulty easy|medium|hard added + wired + the ValueError handled (stderr + exit 2). Re-exported
difficulty. TDD test_difficulty.py (6): deeper mate scores harder (m1<m2<m3); deterministic; band
membership; fail-loud on a bad puzzle; the filter returns that band; an impossible filter (mate_in_3
+ easy) fails loud. Full suite 172 -> 178, ruff + mypy strict clean (9 files).

DONE Step 5 (2026-07-12): tactics.py find_pins(board) + find_skewers(board) (PURE, additive;
local ray-walk consistent with Board.attacks_from geometry). NEW Pin(attacker, front, back,
absolute) + Skewer(attacker, front, back). For each side-to-move slider (B/R/Q) walk each ray:
first enemy = front, next enemy behind = back; back is the enemy KING or value(back) >
value(front) -> PIN (absolute = back is king); value(front) > value(back) -> SKEWER; equal ->
neither. Geometric detection, engine-consistent, CROSS-CHECKED vs python-chess (board.is_pinned).
Re-exported Pin / Skewer / find_pins / find_skewers. TDD test_tactics.py +3: absolute pin
Rd1->Nd7->Kd8 (3k4/3n4/8/8/8/8/8/3RK3 w) absolute=True; skewer Rd1->Qd5->Rd8
(3r4/8/8/3q4/8/8/8/3RK2k w); equal-rooks line -> neither. + a python-chess cross-check
is_pinned(BLACK, D7). Full suite 168 -> 172 in ~3.7s. ruff + mypy strict clean (8 files). NOTE:
pins/skewers are STATIC geometric motifs (correctness is cross-checked, not a material-win
claim); the _forced_gain proof is reserved for forks and can be layered onto a skewer-exploit
MOVE later if a skewer puzzle is wanted.

DONE Step 4 (2026-07-12): NEW palamedes/tactics.py find_forks(board, min_gain=2.0) ->
list[Fork] = ENGINE-VERIFIED forks (never pattern-matched). NEW Board.attacks_from(sq) ->
set[int] (per-piece pseudo-attacks; reuses the engine deltas; pawns = 2 diagonals; sliders
stop at + include the first occupied square). A fork = a legal move whose moved piece then
attacks >= 2 significant enemy targets (>= 2 pieces worth >= 3, OR >= 1 piece + the enemy king
= royal fork) AND provably wins >= min_gain material: net = capture_value(move) -
_forced_gain(child, 1), where _forced_gain is a negamax giving the opponent ONE full defensive
move then _quiesce (capture-only quiescence, stand-pat 0) resolves - so a "fork" refuted by
capturing the forking piece or otherwise saving the material is NOT reported. Fork(uci, san,
targets(square names), gain). Re-exported find_forks + Fork. TDD test_tactics.py (3): royal
knight fork Ng4-f6+ forking Ke8+Qe4 (4k3/8/8/8/4q1N1/8/8/6K1 w) found w/ targets e4/e8, gain
9; the SAME + a black g7 pawn (gxf6 refutes) -> NOT reported; bare kings -> []. + a python-
chess CROSS-CHECK in test_with_chess (fork move legal + gives check + the knight really
attacks the queen square via chess.attacks). Full suite 164 -> 168 in ~3.7s. ruff + mypy
strict clean (8 files). NOTE: attacks_from is a general engine primitive - reuse it (+
_forced_gain / _quiesce) for Step 5 pins/skewers.

DONE Step 3 (2026-07-12): mate-in-3. CONFIRMED engine.forced_mate_move is ALREADY
general-depth (finds a forced mate-in-3; no rewrite needed). Added a VERIFIED bank puzzle
m3-two-rook-ladder (FEN 8/8/8/8/8/6k1/1R6/R5K1 w - -, key Rb4 = b2b4, two-rook ladder), found
empirically via an engine scan: forced_mate_move(2)=None AND forced_mate_move(3)=Rb4 AND
_move_forces_mate(Rb4,3)=True AND NOT _move_forces_mate(Rb4,2) => genuinely mate-in-3;
python-chess is_valid. verifier.verify_solution += a "mate_in_3" branch (reuses
_move_forces_mate(...,3)). cli.GOALS += "mate_in_3" (so --goal mate_in_3 and generate_puzzle
/ --verify-all flow through). NEW tests/test_mate3.py (6): forced mate-in-3 found +
_move_forces_mate(3); genuinely-3-not-2; monotone (mate-in-1 also found at depth 3);
bare-kings -> None; verifier branch; bank puzzle verifies. The new puzzle's FEN auto-joins
test_with_chess REFERENCE_FENS so it is ALSO cross-checked vs python-chess (legal moves / SAN
/ check / parse_san). --verify-all passes ALL puzzles. Full suite 152 -> 164 (now ~5s: the
depth-3 searches cost more). ruff + mypy strict clean. NOTE: K+Q vs K rarely gives exactly-
forced-mate-in-3 (mostly <=2 or the king escapes); TWO-ROOK ladder positions are the reliable
source (used an engine scan over K+R+R-vs-K to find one).

DONE Step 2 (2026-07-12): engine.parse_san(board, san) -> Move NEW (the inverse of
move_to_san). Component parser: strip trailing +/#; castling O-O / O-O-O (0-0 tolerated);
promotion suffix =Q/R/B/N; leading piece letter (pawn by default); strip capture x; last 2
chars = destination square; leading chars = file/rank disambiguation; then select the UNIQUE
legal move matching (destination, moving-piece letter for the side to move, promotion,
disamb file/rank). Fail-loud: non-str -> TypeError; empty / illegal / ambiguous / malformed
-> ValueError. Re-exported from palamedes (__init__ + __all__). TESTS test_san.py (12) incl
a ROUND-TRIP property over 6 positions x every legal move (parse_san(move_to_san(m)) == m -
covers castling / captures / promotion / disambiguation / en-passant / check suffixes) + a
python-chess CROSS-CHECK in test_with_chess (parse_san accepts chess.Board.san(m) and
resolves to the same UCI across REFERENCE_FENS). Full suite 127 -> 152, ruff + mypy strict
clean. NOTE: Move.promotion is stored LOWERCASE (e.g. "q"); move_to_san appends +/# suffixes,
so the round-trip already exercises suffix stripping.

DONE Step 1 (2026-07-12): engine.perft(board, depth) NEW - standard leaf-node counter
(depth 0 -> 1; else sum of perft(push(m), depth-1) over legal_moves; depth < 0 -> ValueError
fail-loud); re-exported from palamedes (__init__ + __all__). NEW tests/test_perft.py pins
move generation against KNOWN reference perft values: startpos 1/2/3 = 20/400/8902; Kiwipete
1/2 = 48/2039; pos3 (8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - -) 1/2/3 = 14/191/2812; pos4
(r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq -) 1/2 = 6/264; pos5
(rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ -) 1/2 = 44/1486. These exercise
castling / en-passant / promotion / checks / pins and ALL MATCH => the engine's legal move
generation is CORRECT (strengthens the engine-verified moat far beyond the single
perft(1)=48). 14 new tests. Full suite 113 -> 127 in 0.55s (perft at these depths is fast).
ruff + mypy --strict clean.

DONE Step 0 (2026-07-12): tooling. NEW pyproject.toml (ruff line100 target py311 select
E/F/W/I/UP/B/SIM ignore SIM108; mypy python 3.11 strict files=palamedes + chess override
ignore_missing_imports; requires-python BUMPED 3.9->3.11 to match CI/tooling - README
badge to fix in Step 9; version 1.0.0; project.scripts palamedes=cli:main). 60 ruff
violations fixed (55 auto UP006/UP045/UP035/UP037 modernise typing.List/Dict/Optional ->
list/dict/|None with future-annotations; manual: 2x SIM109 `p in (a,b)`, 4x SIM102
collapsed the castle nested-ifs, 3x E501, 1x B904 raise-from-None in test_engine, 2x E402
moved test_with_chess's palamedes imports ABOVE the importorskip). 14 mypy --strict errors
fixed: NEW Puzzle TypedDict in fen_bank (id/fen/goal/solution/san/theme required +
threshold NotRequired) threaded through fen_bank/verifier/generator for TYPED field access
(no dict[str,object] cascade); engine.push now guards a None from-square piece (raise
ValueError = fail-loud) which also fixed 3 union-attr errors; verifier._move_forces_mate
got move: Move; fen_bank all_puzzles/get_puzzle use p.copy() not dict(p) to keep the Puzzle
type. CI += ruff + mypy steps (matrix 3.11/3.12/3.13). NEW tests/test_invariants.py:
startpos perft(1)=20, Kiwipete perft(1)=48, generate_puzzle(seed) determinism, subprocess
import-purity (import palamedes pulls NO chess). Gate: 66 core / 113 full pass, ruff clean,
mypy strict clean (7 files). GOTCHA: mypy rejects python_version 3.9 (needs >=3.10) -> set
3.11 + bumped requires-python to match; ruff --fix also modernised cli.py typing (safe).

## Rules
GreenPandaTech noreply only; repo PRIVATE; proprietary licence preserved; zero runtime
deps; verify bare pytest + ruff + mypy --strict each increment; push every green
increment; adversarial review before merge; merge --no-ff + tag v2.0.0 at the end. Full
suite needs python-chess (dev-only; importorskip skips without it). CI runs bare pytest.
Commit messages plain ASCII, no apostrophes/backticks/parens-imbalance.
