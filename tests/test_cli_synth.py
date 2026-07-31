"""CLI synthesis mode: --synth renders one puzzle or emits JSON lines."""

from __future__ import annotations

import json

import pytest

from palamedes.cli import main

# Same empirically chosen fast seeds as tests/test_synth.py (kept local: test
# modules are not importable as a package under bare pytest).
KQK_M1_SEED = 9
KQK_M2_SEED = 9


def test_cli_synth_renders_a_puzzle_with_reveal(capsys):
    rc = main(["--synth", "KQK", "--goal", "mate_in_1", "--seed", str(KQK_M1_SEED), "--reveal"])
    captured = capsys.readouterr()
    assert rc == 0
    assert "Mate in 1" in captured.out
    assert "Solution:" in captured.out
    assert f"synth-kqk-m1-s{KQK_M1_SEED}-p1" in captured.out


def test_cli_synth_defaults_to_mate_in_2(capsys):
    rc = main(["--synth", "KQK", "--seed", str(KQK_M2_SEED)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "Mate in 2" in captured.out
    assert "(Run again with --reveal to see the solution.)" in captured.out


def test_cli_synth_count_emits_json_lines(capsys):
    rc = main(["--synth", "KQK", "--seed", str(KQK_M2_SEED), "--count", "2"])
    captured = capsys.readouterr()
    assert rc == 0
    puzzles = [json.loads(line) for line in captured.out.strip().splitlines()]
    assert [p["id"] for p in puzzles] == [
        f"synth-kqk-m2-s{KQK_M2_SEED}-p1",
        f"synth-kqk-m2-s{KQK_M2_SEED}-p2",
    ]
    assert all(p["goal"] == "mate_in_2" for p in puzzles)
    # The summary goes to stderr, never mixed into the JSON stream.
    assert "Synthesized 2 verified puzzles." in captured.err


def test_cli_synth_exhaustion_is_a_clean_error(capsys):
    rc = main(["--synth", "KNK", "--seed", "0", "--tries", "30"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "Synthesis failed" in captured.err
    assert captured.out == ""


def test_cli_synth_invalid_piece_set_is_a_clean_error(capsys):
    rc = main(["--synth", "KPK", "--seed", "0"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "Synthesis failed" in captured.err
    assert "piece set" in captured.err
    assert captured.out == ""


def test_cli_synth_empty_spec_fails_loud_not_bank_fallthrough(capsys):
    # An explicitly empty spec is a bad piece set like any other: it must
    # never truthiness-skip the synth branch and print a bank puzzle.
    rc = main(["--synth", ""])
    captured = capsys.readouterr()
    assert rc == 2
    assert "Synthesis failed" in captured.err
    assert "piece set" in captured.err
    assert captured.out == ""


def test_cli_count_conflicts_with_solve_and_reveal():
    # --count emits JSON lines; silently dropping the interactive flags would
    # be quiet misuse, so both combinations are parser errors.
    with pytest.raises(SystemExit) as excinfo:
        main(["--synth", "KQK", "--count", "1", "--solve"])
    assert excinfo.value.code == 2
    with pytest.raises(SystemExit) as excinfo:
        main(["--synth", "KQK", "--count", "1", "--reveal"])
    assert excinfo.value.code == 2


def test_cli_synth_rejects_win_material():
    with pytest.raises(SystemExit):
        main(["--synth", "KQK", "--goal", "win_material"])


def test_cli_count_requires_synth():
    with pytest.raises(SystemExit):
        main(["--count", "2"])


def test_cli_tries_requires_synth():
    with pytest.raises(SystemExit):
        main(["--tries", "10"])


def test_cli_synth_conflicts_with_fen_and_mine():
    with pytest.raises(SystemExit):
        main(["--synth", "KQK", "--fen", "6k1/5ppp/8/8/8/8/8/R6K w - - 0 1"])
    with pytest.raises(SystemExit):
        main(["--synth", "KQK", "--mine", "games.pgn"])


def test_cli_synth_conflicts_with_difficulty():
    with pytest.raises(SystemExit):
        main(["--synth", "KQK", "--difficulty", "easy"])
