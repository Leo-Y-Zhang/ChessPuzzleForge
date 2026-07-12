# Session handoff - Palamedes "to the max" (targeting v2.0.0)

> AUTONOMOUS OVERNIGHT MODE (set 2026-07-12): user is away until ~12pm next day.
> Work the program autonomously and SELF-RESUME across usage/5h-window + context
> resets. Every wake: re-anchor from THIS file + the project_repo_max_upgrades
> memory + MEMORY.md, one line project/last-done/next, then execute. Commit+push each
> GREEN increment (GreenPandaTech noreply, PRIVATE repo), keep the "Exact next step"
> current, verify (bare `.venv/Scripts/python -m pytest -q` + ruff + mypy --strict once
> configured) before claiming done, run the adversarial verify before any merge.
> Standing gates: never push secrets, never flip repo visibility public, nothing
> outward/irreversible beyond merge+tag to the PRIVATE repo, proprietary licence kept.
> Reschedule the overnight wakeup each turn. Repo #15 of the program; after Palamedes:
> Mentor, NeuralBox. Prior repos shipped: Kineo v2.0.0 (#13), Lynceus v2.0.0 (#14).

Program: repo max-upgrades #15 (after Lynceus #14 shipped v2.0.0). Palamedes is ALREADY
v1.0.0 (tagged) -> to-the-max targets **v2.0.0**. Spec:
`docs/superpowers/specs/to-the-max.md`. Branch `feature/to-the-max` (cut from the
proprietary-licence commit b54846c on main). Baseline = **62 core tests** (bare pytest,
no chess) / **109 full** (with the dev-only `python-chess` referee). venv at `.venv`
(Windows: `.venv/Scripts/python -m pytest -q`; pip installed pytest + chess + ruff +
mypy). ZERO runtime deps; pure-Python. The moat = an ENGINE-VERIFIED chess puzzle
generator (ships its own engine, PROVES every answer; perft-pinned move gen). CI = bare
`pytest` (root conftest makes `import palamedes` resolve; matrix 3.11/3.12/3.13).

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
- [ ] Step 4 - Verified motif: forks (find_forks, engine-verified double attack + material gain)
- [ ] Step 5 - Verified motifs: pins & skewers (find_pins/find_skewers, geometric + engine-verified)
- [ ] Step 6 - Difficulty scoring + --difficulty filter (pure, deterministic)
- [ ] Step 7 - Interactive solve mode + SAN input in the CLI (additive)
- [ ] Step 8 - Export (PGN + JSON) + golden digest + hostile-input sweep + perf sanity
- [ ] Step 9 - Docs + version 2.0.0 + final adversarial 3-lens review + merge --no-ff + tag v2.0.0

## Exact next step
Step 4 - Verified motif: forks (PURE, additive, TDD) - the hardest/most distinctive step;
keep the verification STRICT (an engine-PROVEN material win, never a pattern guess). Add a
NEW palamedes/tactics.py with `find_forks(board) -> list[...]`: a move by the side to move
that, once played, ATTACKS >= 2 enemy targets (a piece + the king = royal fork, or >= 2
pieces) such that the opponent cannot save the material, netting a material win VERIFIED by
the engine. Approach per legal move m: push; find the moved piece's attacks on enemy pieces
(reuse the engine's attack logic / is_attacked_by / a squares-attacked helper); require >= 2
worthwhile targets; then PROVE the win with a short search - e.g. over the opponent's best
reply, the attacker still wins material (extend the net_material_gain idea, or a 2-3 ply
minimax on material). Return a small record: move (UCI + SAN), forked target squares, and
the proven material gain. HONESTY: only report a fork that genuinely wins. Cross-check a
known knight/royal fork vs python-chess (the attacked squares after the move). Optionally
add a fork puzzle to fen_bank (theme 'fork', goal 'win_material' or a new goal). Fail-loud on
bad FEN. TDD test_tactics.py: a clean royal knight fork winning the queen -> found with the
right move + targets + gain; a quiet position -> []; a FAKE fork where the opponent defends/
recaptures and does NOT lose material -> NOT reported. Verify gate. Commit+push, mark [x],
set Step 5 (pins & skewers). PERF: the whole-board scan x a short per-move search can be
heavy - keep the proof shallow (2-3 ply) and test on sparse positions; watch suite runtime
(mate-in-3 already pushed it to ~5s).

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
