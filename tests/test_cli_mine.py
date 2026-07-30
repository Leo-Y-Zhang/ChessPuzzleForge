"""CLI mining mode: --mine writes JSON lines to stdout, progress to stderr."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from palamedes.cli import main

FIXTURE_PATH = Path(__file__).parent / "data" / "mined_games.pgn"


def test_cli_mine_emits_one_json_line_per_puzzle(capsys):
    rc = main(["--mine", str(FIXTURE_PATH)])
    captured = capsys.readouterr()
    assert rc == 0
    lines = captured.out.strip().splitlines()
    puzzles = [json.loads(line) for line in lines]
    assert [p["id"] for p in puzzles] == [
        "mined-g1-p2-m1",
        "mined-g2-p0-m1",
        "mined-g3-p0-fork",
        "mined-g4-p0-m3",
        "mined-g4-p2-m1",
        "mined-g4-p4-m1",
        "mined-g5-p0-m2",
        "mined-g5-p2-m1",
    ]
    # Progress and the summary go to stderr, never mixed into the JSON stream.
    assert "game 1/5" in captured.err
    assert "Mined 8 verified puzzles." in captured.err


def test_cli_mine_respects_bounds(capsys):
    rc = main(["--mine", str(FIXTURE_PATH), "--max-games", "1"])
    captured = capsys.readouterr()
    assert rc == 0
    ids = [json.loads(line)["id"] for line in captured.out.strip().splitlines()]
    assert ids == ["mined-g1-p2-m1"]


def test_cli_mine_missing_file_is_a_clean_error(capsys):
    rc = main(["--mine", "no-such-file.pgn"])
    captured = capsys.readouterr()
    assert rc == 2
    assert "Cannot read PGN file" in captured.err
    assert captured.out == ""


def test_cli_mine_malformed_pgn_is_a_clean_error(tmp_path, capsys):
    bad = tmp_path / "bad.pgn"
    bad.write_text("1. e4 {never closed\n", encoding="utf-8")
    rc = main(["--mine", str(bad)])
    captured = capsys.readouterr()
    assert rc == 2
    assert "game 1" in captured.err
    assert captured.out == ""


def test_cli_mine_non_utf8_file_is_a_clean_error_not_a_traceback(tmp_path, capsys):
    # Latin-1 PGN files (accented player names) are common in real corpora:
    # undecodable bytes must take the clean exit-2 path, never a traceback.
    latin1 = tmp_path / "latin1.pgn"
    latin1.write_bytes('[White "S\xe9bastien"]\n[Result "*"]\n\n1. e4 *\n'.encode("latin-1"))
    rc = main(["--mine", str(latin1)])
    captured = capsys.readouterr()
    assert rc == 2
    assert "Cannot read PGN file" in captured.err
    assert captured.out == ""


def test_cli_mine_accepts_a_utf8_bom_file(tmp_path, capsys):
    # Windows Notepad writes UTF-8 with a BOM by default; the BOM must not
    # surface as an unrecognised movetext token.
    bom = tmp_path / "bom.pgn"
    bom.write_bytes(b"\xef\xbb\xbf" + b'[Result "0-1"]\n\n1. f3 e5 2. g4 Qh4# 0-1\n')
    rc = main(["--mine", str(bom)])
    captured = capsys.readouterr()
    assert rc == 0
    ids = [json.loads(line)["id"] for line in captured.out.strip().splitlines()]
    assert ids == ["mined-g1-p3-m1"]


def test_cli_bounds_require_mine():
    with pytest.raises(SystemExit) as excinfo:
        main(["--max-games", "3"])
    assert excinfo.value.code == 2
