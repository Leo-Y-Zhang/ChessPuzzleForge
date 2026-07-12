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
- [ ] Step 0 - Tooling: pyproject (ruff E/F/W/I/UP/B/SIM + mypy --strict) + CI lint/type + baseline test
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
Step 0 - Tooling. Add a NEW pyproject.toml: [tool.ruff] line-length 100, target py311,
lint select E/F/W/I/UP/B/SIM (ignore SIM108 like the other repos); [tool.mypy]
python_version 3.11, strict = true, files = ["palamedes"] (add an override
ignore_missing_imports for `chess` in case a stray import appears - but the shipped core
must NOT import chess). Fix the ~14 mypy --strict errors (start: generator.py:86 Missing
type args for Dict -> dict[...]; sweep the rest) + any ruff UP nits (the engine uses
typing.List/Optional/Iterable -> modernise to list/|None where UP flags them, KEEP
`from __future__ import annotations`). Extend .github/workflows/ci.yml to add a ruff step
and a mypy step (matrix 3.11/3.12/3.13 already runs pytest). Add tests/test_invariants.py:
perft(1) startpos = 20 AND Kiwipete perft(1) = 48 (engine sanity), determinism of
generate_puzzle(seed) (same seed -> same puzzle), and a fresh-subprocess proof that
`import palamedes` does NOT import `chess`. Verify bare pytest (62 core / 109 full) + ruff
+ mypy --strict all clean. Commit+push, mark [x], set Step 1 (perft harness). NOTE: bank
tests + engine already green; keep the dev-only chess referee importorskip-guarded.

## Rules
GreenPandaTech noreply only; repo PRIVATE; proprietary licence preserved; zero runtime
deps; verify bare pytest + ruff + mypy --strict each increment; push every green
increment; adversarial review before merge; merge --no-ff + tag v2.0.0 at the end. Full
suite needs python-chess (dev-only; importorskip skips without it). CI runs bare pytest.
Commit messages plain ASCII, no apostrophes/backticks/parens-imbalance.
