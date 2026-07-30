"""PGN corpus mining: replay games, prefilter, search, verify, emit.

The toy fixture (tests/data/mined_games.pgn) is five short games with known
findable tactics - its movetext includes a castling move (O-O) and a promotion
(bxa8=Q#) - and the mined output is pinned EXACTLY: ids, FENs, goals, solutions,
SAN and themes. The realistic fixture (tests/data/opera_game.pgn) is a real
full-length game whose positions reach 32 men: it pins that mining ordinary
games is fast (the original pipeline stalled for 15+ minutes on one such
position) and that its mined output is exact. Every mined puzzle must also
independently re-pass the verifier, and malformed input must fail loud.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from palamedes.engine import Board, forced_mate_move
from palamedes.miner import mine_games, mine_pgn
from palamedes.pgn import PgnError, read_games
from palamedes.verifier import verify_puzzle

FIXTURE = (Path(__file__).parent / "data" / "mined_games.pgn").read_text(encoding="utf-8")
OPERA = (Path(__file__).parent / "data" / "opera_game.pgn").read_text(encoding="utf-8")

EXPECTED = [
    {
        # Game A, after 1. O-O Kh8: the castled rook mates on the back rank.
        "id": "mined-g1-p2-m1",
        "fen": "7k/6pp/8/8/8/8/6PP/5RK1 w - - 2 2",
        "goal": "mate_in_1",
        "solution": ["f1f8"],
        "san": "Rf8#",
        "theme": "mined mate-in-one",
    },
    {
        # Game B, initial position: promoting to a queen OR a rook both mate.
        "id": "mined-g2-p0-m1",
        "fen": "r5k1/1P3ppp/8/8/8/8/5PPP/6K1 w - - 0 1",
        "goal": "mate_in_1",
        "solution": ["b7a8q", "b7a8r"],
        "san": "bxa8=Q#, bxa8=R#",
        "theme": "mined mate-in-one",
    },
    {
        # Game C, initial position: Nxe5 grabs a pawn and forks queen + rook.
        # The threshold is what the verifier's recapture model proves for the
        # first move (the pawn); the fork itself nets a full exchange later.
        "id": "mined-g3-p0-fork",
        "fen": "6k1/3r3p/2q3p1/4p3/8/5N2/5PPP/5RK1 w - - 0 1",
        "goal": "win_material",
        "solution": ["f3e5"],
        "san": "Nxe5",
        "threshold": 1.0,
        "theme": "mined knight fork",
    },
    {
        # Game D, initial position: the bank's two-rook-ladder mate in 3,
        # rediscovered from scratch (same key move as the curated answer).
        "id": "mined-g4-p0-m3",
        "fen": "8/8/8/8/8/6k1/1R6/R5K1 w - - 0 1",
        "goal": "mate_in_3",
        "solution": ["b2b4"],
        "san": "Rb4 (then mate within three)",
        "theme": "mined mate-in-three",
    },
    {
        # Game D, after 1. Rb4 Kh3: the game played the slower 2. Rab1, but the
        # position holds an immediate mate, and the miner prefers least depth.
        "id": "mined-g4-p2-m1",
        "fen": "8/8/8/8/1R6/7k/8/R5K1 w - - 2 2",
        "goal": "mate_in_1",
        "solution": ["a1a3"],
        "san": "Ra3#",
        "theme": "mined mate-in-one",
    },
    {
        # Game D, after 2. Rab1 Kg3: only the b1 rook mates (the b4 rook must
        # keep guarding the king's fourth-rank escape squares).
        "id": "mined-g4-p4-m1",
        "fen": "8/8/8/8/1R6/6k1/8/1R4K1 w - - 4 3",
        "goal": "mate_in_1",
        "solution": ["b1b3"],
        "san": "R1b3#",
        "theme": "mined mate-in-one",
    },
    {
        # Game E, initial position: a quiet KING move forces mate in two.
        "id": "mined-g5-p0-m2",
        "fen": "8/8/8/8/8/3Q4/k7/2K5 w - - 0 1",
        "goal": "mate_in_2",
        "solution": ["c1c2"],
        "san": "Kc2 (then mate next move)",
        "theme": "mined mate-in-two",
    },
    {
        # Game E, after 1. Kc2 Ka1: two queen moves deliver the mate.
        "id": "mined-g5-p2-m1",
        "fen": "8/8/8/8/8/3Q4/2K5/k7 w - - 2 2",
        "goal": "mate_in_1",
        "solution": ["d3a6", "d3a3"],
        "san": "Qa6#, Qa3#",
        "theme": "mined mate-in-one",
    },
]


def test_fixture_movetext_contains_castling_and_promotion():
    games = read_games(FIXTURE)
    all_moves = [move for game in games for move in game.moves]
    assert "O-O" in all_moves
    assert any("=" in move for move in all_moves)


def test_mined_output_matches_the_expected_set_exactly():
    assert mine_pgn(FIXTURE) == EXPECTED


def test_every_mined_puzzle_independently_re_passes_the_verifier():
    for puzzle in mine_pgn(FIXTURE):
        ok, message = verify_puzzle(puzzle)
        assert ok, f"{puzzle['id']}: {message}"


def test_mining_is_deterministic_on_repeat():
    assert mine_pgn(FIXTURE) == mine_pgn(FIXTURE)


def test_max_games_bounds_the_games_mined():
    mined = mine_pgn(FIXTURE, max_games=1)
    assert [p["id"] for p in mined] == ["mined-g1-p2-m1"]


def test_max_plies_bounds_the_replay_depth():
    # With no plies replayed, only each game's initial position is scanned.
    mined = mine_pgn(FIXTURE, max_plies=0)
    assert [p["id"] for p in mined] == [
        "mined-g2-p0-m1",
        "mined-g3-p0-fork",
        "mined-g4-p0-m3",
        "mined-g5-p0-m2",
    ]


def test_progress_reports_one_line_per_game():
    messages: list[str] = []
    mine_pgn(FIXTURE, progress=messages.append)
    assert len(messages) == 5
    assert messages[0].startswith("game 1/5:")
    assert "new puzzles" in messages[0]


def test_games_without_a_fen_tag_start_from_the_standard_position():
    # Fool's mate: the position before 2... Qh4# is mined as a mate in 1.
    mined = mine_pgn('[Result "0-1"]\n\n1. f3 e5 2. g4 Qh4# 0-1\n')
    assert [p["id"] for p in mined] == ["mined-g1-p3-m1"]
    assert mined[0]["solution"] == ["d8h4"]
    assert mined[0]["san"] == "Qh4#"


def test_duplicate_positions_are_mined_once():
    # The same game twice: the second pass adds nothing (dedupe by position).
    text = '[Result "0-1"]\n\n1. f3 e5 2. g4 Qh4# 0-1\n'
    assert len(mine_pgn(text + "\n" + text)) == 1


def test_mining_a_small_file_completes_in_seconds():
    start = time.perf_counter()
    mine_pgn(FIXTURE)
    elapsed = time.perf_counter() - start
    assert elapsed < 30.0, f"mining the fixture unexpectedly slow: {elapsed:.2f}s"


# --------------------------------------------------- a real full-length game
OPERA_EXPECTED = [
    {
        # Before 15. Bxd7+: the bishop grabs the d7 rook; after the forced
        # recapture White is an exchange up (Morphy's actual move).
        "id": "mined-g1-p28-fork",
        "fen": "4kb1r/p2r1ppp/4qn2/1B2p1B1/4P3/1Q6/PPP2PPP/2KR4 w k - 2 15",
        "goal": "win_material",
        "solution": ["b5d7"],
        "san": "Bxd7+",
        "threshold": 2.0,
        "theme": "mined bishop fork",
    },
    {
        # Before 16. Qb8+: the queen sacrifice forces 16... Nxb8 17. Rd8#.
        # Found by the large-board checks-only scan (21 men on the board).
        "id": "mined-g1-p30-m2",
        "fen": "4kb1r/p2n1ppp/4q3/4p1B1/4P3/1Q6/PPP2PPP/2KR4 w k - 0 16",
        "goal": "mate_in_2",
        "solution": ["b3b8"],
        "san": "Qb8+ (then mate next move)",
        "theme": "mined mate-in-two",
    },
    {
        # Before 17. Rd8#: the famous final mate.
        "id": "mined-g1-p32-m1",
        "fen": "1n2kb1r/p4ppp/4q3/4p1B1/4P3/8/PPP2PPP/2KR4 w k - 0 17",
        "goal": "mate_in_1",
        "solution": ["d1d8"],
        "san": "Rd8#",
        "theme": "mined mate-in-one",
    },
]


def test_mining_a_real_full_length_game_is_fast_and_exactly_pinned():
    # The Opera game replays through 32-man opening positions - exactly the
    # inputs --mine advertises. The unprefiltered pipeline used to stall for
    # 15+ minutes on a single such position; the bound here is generous.
    start = time.perf_counter()
    mined = mine_pgn(OPERA)
    elapsed = time.perf_counter() - start
    assert mined == OPERA_EXPECTED
    assert elapsed < 30.0, f"mining a real game unexpectedly slow: {elapsed:.2f}s"


def test_every_opera_puzzle_independently_re_passes_the_verifier():
    for puzzle in mine_pgn(OPERA):
        ok, message = verify_puzzle(puzzle)
        assert ok, f"{puzzle['id']}: {message}"


def test_quiet_key_mate_in_2_on_a_large_board_is_missed_by_design():
    # Game E's quiet-king-move mate in 2, padded with pawns to 11 men: the mate
    # is real (the full-width search proves it) but above the small-position
    # cutoff the miner scans checking key moves only, so nothing is emitted.
    # This pins the documented recall trade that keeps real-game mining fast.
    fen = "8/4pppp/8/8/8/3Q4/k3PPPP/2K5 w - - 0 1"
    assert forced_mate_move(Board.from_fen(fen), 2) == "c1c2"  # the mate exists
    text = f'[SetUp "1"]\n[FEN "{fen}"]\n[Result "*"]\n\n*\n'
    assert mine_pgn(text) == []


# ------------------------------------------------------------ loud failures
def test_illegal_move_in_a_game_fails_loud_naming_the_game():
    with pytest.raises(PgnError, match=r"game 1.*move 1.*'e5'"):
        mine_pgn('[Result "*"]\n\n1. e5 e5 *\n')  # e5 is not legal from the start


def test_invalid_fen_tag_fails_loud_naming_the_game():
    with pytest.raises(PgnError, match=r"game 1.*FEN"):
        mine_pgn('[SetUp "1"]\n[FEN "not a fen"]\n\n1. e4 *\n')


def test_malformed_pgn_propagates_the_reader_error():
    with pytest.raises(PgnError, match=r"game 1"):
        mine_pgn("1. e4 {never closed\n")


def test_negative_bounds_are_rejected():
    games = read_games('[Result "*"]\n\n1. e4 *\n')
    with pytest.raises(ValueError):
        mine_games(games, max_games=-1)
    with pytest.raises(ValueError):
        mine_games(games, max_plies=-1)
