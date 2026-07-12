"""CLI tests - pure standard library.  Exercise the public entry point."""

from __future__ import annotations

from palamedes.cli import main


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


# The derived mate-in-1 for this position is Ra8# (UCI a1a8).
MATE1_FEN = "6k1/5ppp/8/8/8/8/8/R6K w - - 0 1"


def test_solve_accepts_the_correct_san(capsys):
    rc = main(["--fen", MATE1_FEN, "--solve"], reader=lambda _prompt: "Ra8")
    assert rc == 0
    assert "correct" in capsys.readouterr().out.lower()


def test_solve_accepts_the_correct_uci(capsys):
    rc = main(["--fen", MATE1_FEN, "--solve"], reader=lambda _prompt: "a1a8")
    assert rc == 0
    assert "correct" in capsys.readouterr().out.lower()


def test_solve_wrong_move_gives_a_hint(capsys):
    rc = main(["--fen", MATE1_FEN, "--solve"], reader=lambda _prompt: "Ra7")
    out = capsys.readouterr().out.lower()
    assert rc == 0
    assert "not the solution" in out
    assert "hint" in out


def test_solve_illegal_move_is_a_clean_error(capsys):
    rc = main(["--fen", MATE1_FEN, "--solve"], reader=lambda _prompt: "Qz9")
    captured = capsys.readouterr()
    assert rc == 2
    assert "legal" in (captured.out + captured.err).lower()
