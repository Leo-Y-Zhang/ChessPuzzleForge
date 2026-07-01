"""CLI tests - pure standard library.  Exercise the public entry point."""

from __future__ import annotations

from chesspuzzle.cli import main


def test_cli_list(capsys):
    rc = main(["--list"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "m1-backrank-rook" in out
    assert "win_material" in out


def test_cli_verify_all_passes(capsys):
    rc = main(["--verify-all"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "FAIL" not in out
    assert "All puzzles verified." in out


def test_cli_random_puzzle_hidden_by_default(capsys):
    rc = main(["--seed", "5"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "FEN:" in out
    assert "Solution:" not in out
    assert "--reveal" in out


def test_cli_reveal_prints_solution(capsys):
    rc = main(["--goal", "mate_in_1", "--seed", "5", "--reveal"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Solution:" in out


def test_cli_fen_derivation(capsys):
    rc = main(["--fen", "6k1/5ppp/8/8/8/8/8/R6K w - - 0 1", "--reveal"])
    out = capsys.readouterr().out
    assert rc == 0
    # SAN with the mate marker is the headline; UCI is still shown for reference.
    assert "Ra8#" in out
    assert "a1a8" in out


def test_cli_fen_invalid_returns_friendly_error(capsys):
    rc = main(["--fen", "totally not a fen", "--reveal"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "Invalid FEN" in err


def test_cli_fen_no_mate_returns_error(capsys):
    rc = main(["--fen", "8/8/8/8/8/8/8/k6K w - - 0 1"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "No mate-in-1" in err
