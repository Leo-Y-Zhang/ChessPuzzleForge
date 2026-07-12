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
- [ ] Step 1 - Perft correctness harness (perft(board,depth) + known-value reference table)
- [ ] Step 2 - SAN parse (parse_san w/ full disambiguation; round-trip; cross-check chess)
- [ ] Step 3 - Mate-in-3 search (forced_mate_in_n up to 3, perf-bounded, verified)
- [ ] Step 4 - Verified motif: forks (find_forks, engine-verified double attack + material gain)
- [ ] Step 5 - Verified motifs: pins & skewers (find_pins/find_skewers, geometric + engine-verified)
- [ ] Step 6 - Difficulty scoring + --difficulty filter (pure, deterministic)
- [ ] Step 7 - Interactive solve mode + SAN input in the CLI (additive)
- [ ] Step 8 - Export (PGN + JSON) + golden digest + hostile-input sweep + perf sanity
- [ ] Step 9 - Docs + version 2.0.0 + final adversarial 3-lens review + merge --no-ff + tag v2.0.0

## Exact next step
Step 1 - Perft correctness harness (PURE, additive, TDD). Add `perft(board, depth)` to
engine.py (the standard move-generation node counter: sum of perft(push(m), depth-1)
over legal_moves; depth 0 -> 1). Add tests/test_perft.py pinning it against KNOWN
reference values: startpos perft(1)=20, perft(2)=400, perft(3)=8902; Kiwipete
(r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq -) perft(1)=48,
perft(2)=2039; "position 3" (8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - -) perft(1)=14,
perft(2)=191; "position 4" (r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq -)
perft(1)=6. Keep depths SHALLOW (avoid perft(4)+ startpos = ~197k nodes, slow in pure
Python; perft(3) startpos 8902 is fine). This is a STRONG move-gen pin far beyond the
single perft(1)=48. Optional `perft_divide(board, depth) -> dict[str,int]` (per-root-move
counts) for debugging - if added, mypy-annotate it. Re-export perft in __init__ if useful.
Verify bare pytest + ruff + mypy --strict. Commit+push, mark [x], set Step 2 (SAN parse).

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
