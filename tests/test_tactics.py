"""Verified tactics: a fork is reported ONLY if the engine PROVES it wins material.

The key honesty test is that a refuted "fork" (the opponent captures the forking
piece, or otherwise saves the material) is NOT reported.
"""

from palamedes.engine import Board
from palamedes.tactics import find_forks

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
