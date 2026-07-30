"""Seeded endgame synthesis: sample bounded piece sets, prove, verify, emit.

The synthesizer samples positions from a bounded piece set (e.g. KQK, KRRK)
deterministically from a seed, keeps only positions where the existing prover
finds a forced mate in EXACTLY the requested number of moves, and re-proves
every accepted puzzle through verify_puzzle before it is returned. These tests
pin: the emitted shape and piece census, exactness (a mate-in-2 puzzle has no
mate in 1), determinism (same seed -> byte-identical puzzles), fail-loud
behaviour on hopeless sets and malformed specs, and the accept gate (a puzzle
that fails verification is never emitted).

Seeds below were chosen once so each search succeeds within a few dozen
samples; determinism makes them stable.
"""

from __future__ import annotations

import pytest

from palamedes.difficulty import difficulty
from palamedes.engine import Board, forced_mate_move
from palamedes.generator import derive_mate_in_1
from palamedes.synth import parse_piece_set, synthesize_puzzle, synthesize_puzzles
from palamedes.verifier import verify_puzzle

# Seeds chosen empirically (deterministic thereafter): each finds its puzzle
# within a small number of samples so the default suite stays fast.
KQK_M1_SEED = 9
KQK_M2_SEED = 9
KRK_M2_SEED = 9
KRRK_M3_SEED = 0


def _census(fen: str) -> dict[str, int]:
    board = Board.from_fen(fen)
    counts: dict[str, int] = {}
    for sq in range(64):
        piece = board.piece_at(sq)
        if piece is not None:
            counts[piece] = counts.get(piece, 0) + 1
    return counts


# ------------------------------------------------------------- happy paths


def test_synthesized_mate_in_1_is_verified_and_matches_the_piece_set():
    puzzle = synthesize_puzzle("KQK", mate_in=1, seed=KQK_M1_SEED)
    assert puzzle["goal"] == "mate_in_1"
    assert puzzle["theme"] == "synthesized KQK mate-in-one"
    assert puzzle["id"] == f"synth-kqk-m1-s{KQK_M1_SEED}-p1"
    # Exactly the requested material: white K+Q versus the bare black king.
    assert _census(puzzle["fen"]) == {"K": 1, "Q": 1, "k": 1}
    assert Board.from_fen(puzzle["fen"]).turn == "w"
    # Every mating move is listed (same discovery the generator uses).
    assert puzzle["solution"] == derive_mate_in_1(puzzle["fen"])
    # And the puzzle independently re-passes the verifier.
    ok, message = verify_puzzle(puzzle)
    assert ok, message


def test_synthesized_mate_in_2_is_exact_not_a_disguised_mate_in_1():
    puzzle = synthesize_puzzle("KQK", mate_in=2, seed=KQK_M2_SEED)
    assert puzzle["goal"] == "mate_in_2"
    assert len(puzzle["solution"]) == 1
    assert "(then mate next move)" in puzzle["san"]
    board = Board.from_fen(puzzle["fen"])
    # Exactness: the prover finds mate in 2 but there is NO mate in 1.
    assert forced_mate_move(board, 1) is None
    assert forced_mate_move(board, 2) is not None
    ok, message = verify_puzzle(puzzle)
    assert ok, message


def test_synthesized_rook_mate_in_2_uses_only_the_requested_material():
    puzzle = synthesize_puzzle("KRK", mate_in=2, seed=KRK_M2_SEED)
    assert _census(puzzle["fen"]) == {"K": 1, "R": 1, "k": 1}
    assert forced_mate_move(Board.from_fen(puzzle["fen"]), 1) is None
    ok, message = verify_puzzle(puzzle)
    assert ok, message


def test_synthesized_mate_in_3_is_exact():
    puzzle = synthesize_puzzle("KRRK", mate_in=3, seed=KRRK_M3_SEED)
    assert puzzle["goal"] == "mate_in_3"
    assert _census(puzzle["fen"]) == {"K": 1, "R": 2, "k": 1}
    board = Board.from_fen(puzzle["fen"])
    # Genuinely three: no forced mate in two exists.
    assert forced_mate_move(board, 2) is None
    ok, message = verify_puzzle(puzzle)
    assert ok, message


def test_same_seed_same_puzzles_and_distinct_positions():
    first = synthesize_puzzles("KQK", mate_in=2, count=2, seed=KQK_M2_SEED)
    second = synthesize_puzzles("KQK", mate_in=2, count=2, seed=KQK_M2_SEED)
    assert first == second  # byte-for-byte deterministic
    assert len(first) == 2
    assert first[0]["fen"] != first[1]["fen"]  # deduped by position
    assert [p["id"] for p in first] == [
        f"synth-kqk-m2-s{KQK_M2_SEED}-p1",
        f"synth-kqk-m2-s{KQK_M2_SEED}-p2",
    ]


def test_single_puzzle_call_matches_the_batch_head():
    single = synthesize_puzzle("KQK", mate_in=2, seed=KQK_M2_SEED)
    batch = synthesize_puzzles("KQK", mate_in=2, count=2, seed=KQK_M2_SEED)
    assert single == batch[0]


def test_synthesized_puzzles_score_with_the_difficulty_model():
    puzzle = synthesize_puzzle("KQK", mate_in=1, seed=KQK_M1_SEED)
    assert difficulty(puzzle)["band"] in ("easy", "medium", "hard")


def test_unseeded_synthesis_still_emits_a_verified_puzzle():
    # A generous budget makes exhaustion astronomically unlikely for KQK m1
    # (the only unseeded - and therefore unpinned - test in this file).
    puzzle = synthesize_puzzle("KQK", mate_in=1, max_tries=20000)
    assert puzzle["id"] == "synth-kqk-m1-p1"  # no seed component when unseeded
    ok, message = verify_puzzle(puzzle)
    assert ok, message


# ---------------------------------------------------------------- fail loud


def test_piece_set_parsing_accepts_lowercase_and_normalises():
    assert parse_piece_set("krk") == "R"
    assert parse_piece_set(" KQRK ") == "QR"


@pytest.mark.parametrize(
    "spec",
    ["", "K", "KK", "QK", "KQ", "KPK", "KKK", "KQQQQK", "KXK", "KQKR"],
)
def test_malformed_piece_sets_fail_loud(spec):
    with pytest.raises(ValueError, match="piece set"):
        parse_piece_set(spec)


def test_hopeless_piece_set_exhausts_and_fails_loud():
    # A lone knight can never mate: the budget runs out and says so, rather
    # than silently downgrading the goal or looping forever.
    with pytest.raises(ValueError, match="no mate_in_2"):
        synthesize_puzzle("KNK", mate_in=2, seed=0, max_tries=40)


@pytest.mark.parametrize("mate_in", [0, 4, -1])
def test_unsupported_depth_fails_loud(mate_in):
    with pytest.raises(ValueError, match="mate_in"):
        synthesize_puzzle("KQK", mate_in=mate_in, seed=0)


def test_bad_count_and_bad_budget_fail_loud():
    with pytest.raises(ValueError, match="count"):
        synthesize_puzzles("KQK", mate_in=1, count=0, seed=0)
    with pytest.raises(ValueError, match="max_tries"):
        synthesize_puzzle("KQK", mate_in=1, seed=0, max_tries=0)


# ------------------------------------------------------------- accept gate


def test_a_candidate_that_fails_verification_is_never_emitted(monkeypatch):
    # Force the verifier to reject everything: synthesis must raise, not emit.
    calls: list[str] = []

    def rejecting_verify(puzzle):
        calls.append(puzzle["id"])
        return False, "forced failure for the accept-gate test"

    monkeypatch.setattr("palamedes.synth.verify_puzzle", rejecting_verify)
    with pytest.raises(AssertionError, match="failed verification"):
        synthesize_puzzle("KQK", mate_in=1, seed=KQK_M1_SEED)
    assert calls  # the gate really ran (and rejected) the candidate
