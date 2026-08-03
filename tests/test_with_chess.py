"""Optional cross-checks against the reference ``python-chess`` library.

These tests independently confirm that the project's pure-Python engine agrees
with a mature reference implementation.  If ``python-chess`` is not installed
the whole module is skipped cleanly (it is NOT a required dependency of the
tested core).
"""

from __future__ import annotations

import pytest

from chesspuzzleforge.engine import Board, move_to_san, parse_san
from chesspuzzleforge.fen_bank import PUZZLES
from chesspuzzleforge.tactics import find_forks, find_pins

# Pass ``exc_type=ImportError`` so pytest skips cleanly when the optional
# ``python-chess`` package is simply absent, without the default (soon-to-be
# error in pytest 9.1) PytestDeprecationWarning about catching ImportError.
chess = pytest.importorskip("chess", exc_type=ImportError)

REFERENCE_FENS = [p["fen"] for p in PUZZLES] + [
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
    "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQ - 0 1",
    "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3",
    "8/P7/8/8/8/8/8/k6K w - - 0 1",
]


@pytest.mark.parametrize("fen", REFERENCE_FENS)
def test_legal_moves_match_reference(fen):
    mine = sorted(m.uci() for m in Board.from_fen(fen).legal_moves())
    theirs = sorted(m.uci() for m in chess.Board(fen).legal_moves)
    assert mine == theirs


@pytest.mark.parametrize("fen", REFERENCE_FENS)
def test_san_matches_reference_for_every_legal_move(fen):
    ref = chess.Board(fen)
    ref_san_by_uci = {m.uci(): ref.san(m) for m in ref.legal_moves}
    for move in Board.from_fen(fen).legal_moves():
        mine = move_to_san(Board.from_fen(fen), move)
        assert mine == ref_san_by_uci[move.uci()], (
            f"SAN mismatch in {fen} for {move.uci()}: "
            f"mine={mine!r} ref={ref_san_by_uci[move.uci()]!r}"
        )


@pytest.mark.parametrize("fen", REFERENCE_FENS)
def test_parse_san_accepts_reference_san(fen):
    # Feed our parser the SAN produced by the mature reference library and confirm
    # it resolves to the same move - an independent check of parse_san.
    ref = chess.Board(fen)
    board = Board.from_fen(fen)
    for m in ref.legal_moves:
        ref_san = ref.san(m)
        parsed = parse_san(board, ref_san)
        assert parsed.uci() == m.uci(), (
            f"parse_san({ref_san!r}) in {fen} -> {parsed.uci()} != {m.uci()}"
        )


def test_find_forks_royal_fork_agrees_with_reference():
    fen = "4k3/8/8/8/4q1N1/8/8/6K1 w - - 0 1"
    forks = find_forks(Board.from_fen(fen))
    assert len(forks) == 1
    cb = chess.Board(fen)
    assert cb.is_valid()
    mv = chess.Move.from_uci(forks[0].uci)
    assert mv in cb.legal_moves
    assert cb.gives_check(mv)          # the fork move is a check per the reference
    cb.push(mv)
    assert chess.E4 in cb.attacks(chess.F6)  # the knight really attacks the queen


def test_find_pins_absolute_pin_agrees_with_reference():
    fen = "3k4/3n4/8/8/8/8/8/3RK3 w - - 0 1"  # Rd1 pins Nd7 to Kd8
    pins = find_pins(Board.from_fen(fen))
    assert len(pins) == 1 and pins[0].absolute
    cb = chess.Board(fen)
    assert cb.is_valid()
    assert cb.is_pinned(chess.BLACK, chess.D7)  # the reference confirms the pin


@pytest.mark.parametrize("fen", REFERENCE_FENS)
def test_check_and_checkmate_match_reference(fen):
    mine = Board.from_fen(fen)
    ref = chess.Board(fen)
    assert mine.is_check() == ref.is_check()
    assert mine.is_checkmate() == ref.is_checkmate()
    assert mine.is_stalemate() == ref.is_stalemate()


@pytest.mark.parametrize(
    "puzzle",
    [p for p in PUZZLES if p["goal"] == "mate_in_1"],
    ids=[p["id"] for p in PUZZLES if p["goal"] == "mate_in_1"],
)
def test_mate_in_1_solutions_are_mate_in_reference(puzzle):
    for uci in puzzle["solution"]:
        board = chess.Board(puzzle["fen"])
        board.push_uci(uci)
        assert board.is_checkmate(), f"{puzzle['id']} {uci} not mate per python-chess"


def _can_force_mate(board, n):
    """True if the side to move in ``board`` can force mate within ``n`` moves.

    Reference implementation on top of python-chess, used only to cross-check
    the project's own search.
    """
    if n <= 0:
        return False
    for move in board.legal_moves:
        after_move = board.copy()
        after_move.push(move)
        if after_move.is_checkmate():
            return True
        if n >= 2:
            replies = list(after_move.legal_moves)
            if not replies:
                continue  # stalemate: this attacking move does not mate
            if all(_defender_reply_still_loses(after_move, r, n - 1) for r in replies):
                return True
    return False


def _defender_reply_still_loses(defender_board, reply, n):
    after_reply = defender_board.copy()
    after_reply.push(reply)
    return _can_force_mate(after_reply, n)


@pytest.mark.parametrize(
    "puzzle",
    [p for p in PUZZLES if p["goal"] == "mate_in_2"],
    ids=[p["id"] for p in PUZZLES if p["goal"] == "mate_in_2"],
)
def test_mate_in_2_solutions_force_mate_in_reference(puzzle):
    for uci in puzzle["solution"]:
        board = chess.Board(puzzle["fen"])
        board.push_uci(uci)  # play the key move; now the defender is to move
        # After the key move every defender reply must allow mate in one.
        replies = list(board.legal_moves)
        assert replies, f"{puzzle['id']} {uci} leaves no reply (should be mate in two, not one)"
        assert all(_can_force_mate((lambda b, r: (b.push(r), b)[1])(board.copy(), reply), 1)
                   for reply in replies), (
            f"{puzzle['id']} {uci} does not force mate in two per python-chess"
        )
