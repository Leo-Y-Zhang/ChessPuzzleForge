"""Verified tactics: a fork is reported ONLY if the engine PROVES it wins material.

The key honesty test is that a refuted "fork" (the opponent captures the forking
piece, or otherwise saves the material) is NOT reported.
"""

from palamedes.engine import Board
from palamedes.tactics import find_forks, find_pins, find_skewers

# White Ng4-f6+ forks the black king (e8) and queen (e4); the knight is safe, so
# after the king moves White plays Nxe4 and wins the queen.
ROYAL_FORK = "4k3/8/8/8/4q1N1/8/8/6K1 w - - 0 1"
# Same, but a black pawn on g7 refutes with ...gxf6 (captures the knight) - so it
# is NOT a winning fork.
FAKE_FORK = "4k3/6p1/8/8/4q1N1/8/8/6K1 w - - 0 1"
QUIET = "4k3/8/8/8/8/8/8/4K3 w - - 0 1"  # bare kings, nothing to fork


def test_finds_a_winning_royal_fork():
    forks = find_forks(Board.from_fen(ROYAL_FORK))
    assert len(forks) == 1
    fork = forks[0]
    assert fork.uci == "g4f6"
    assert "Nf6" in fork.san
    assert set(fork.targets) >= {"e4", "e8"}
    assert fork.gain >= 8.0  # wins the queen


def test_refuted_fork_is_not_reported():
    assert find_forks(Board.from_fen(FAKE_FORK)) == []


def test_quiet_position_has_no_forks():
    assert find_forks(Board.from_fen(QUIET)) == []


# White Rd1 pins the black knight d7 to the black king d8 (absolute pin).
ABSOLUTE_PIN = "3k4/3n4/8/8/8/8/8/3RK3 w - - 0 1"
# White Rd1 skewers the black queen d5 (front) to the rook d8 (back).
SKEWER = "3r4/8/8/3q4/8/8/8/3RK2k w - - 0 1"
# Two equal rooks on the d-file behind the black front rook: neither pin nor skewer.
EQUAL_LINE = "3r4/8/8/3r4/8/8/8/3RK2k w - - 0 1"


def test_finds_absolute_pin():
    pins = find_pins(Board.from_fen(ABSOLUTE_PIN))
    assert len(pins) == 1
    pin = pins[0]
    assert (pin.attacker, pin.front, pin.back) == ("d1", "d7", "d8")
    assert pin.absolute is True


def test_finds_skewer():
    skewers = find_skewers(Board.from_fen(SKEWER))
    assert len(skewers) == 1
    sk = skewers[0]
    assert (sk.attacker, sk.front, sk.back) == ("d1", "d5", "d8")


def test_equal_pieces_line_is_neither_pin_nor_skewer():
    board = Board.from_fen(EQUAL_LINE)
    assert find_pins(board) == []
    assert find_skewers(board) == []
