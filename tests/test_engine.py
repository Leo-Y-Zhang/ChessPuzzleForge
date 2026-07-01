"""Engine tests - pure standard library, no third-party dependencies."""

from __future__ import annotations

from chesspuzzle.engine import (
    Board,
    move_from_uci,
    move_to_san,
    parse_square,
    square_name,
)


def san(fen, uci):
    board = Board.from_fen(fen)
    return move_to_san(board, move_from_uci(board, uci))


def uci_set(fen):
    return {m.uci() for m in Board.from_fen(fen).legal_moves()}


def test_square_helpers_roundtrip():
    for name in ("a1", "h1", "a8", "h8", "e4", "d5"):
        assert square_name(parse_square(name)) == name


def test_fen_roundtrip_startpos():
    fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    assert Board.from_fen(fen).to_fen() == fen


def test_startpos_has_twenty_legal_moves():
    assert len(uci_set("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")) == 20


def test_black_reply_after_e4_has_twenty_moves():
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    assert len(uci_set(fen)) == 20


def test_kiwipete_move_count_matches_known_perft():
    # Kiwipete perft(1) is a well-known reference value of 48 legal moves;
    # it exercises castling and pins, so agreement is strong evidence the
    # move generator is correct.
    fen = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQ - 0 1"
    moves = uci_set(fen)
    assert len(moves) == 48
    assert "e1g1" in moves  # king-side castle
    assert "e1c1" in moves  # queen-side castle


def test_en_passant_capture_is_generated():
    fen = "rnbqkbnr/ppp1p1pp/8/3pPp2/8/8/PPPP1PPP/RNBQKBNR w KQkq f6 0 3"
    assert "e5f6" in uci_set(fen)


def test_promotion_generates_all_four_pieces():
    fen = "8/P7/8/8/8/8/8/k6K w - - 0 1"
    moves = uci_set(fen)
    assert {"a7a8q", "a7a8r", "a7a8b", "a7a8n"} <= moves
    assert len(moves) == 7  # 4 promotions + 3 king moves


def test_checkmate_detection_backrank():
    # Position AFTER Ra8#: black king g8 is checkmated.
    board = Board.from_fen("R5k1/5ppp/8/8/8/8/8/7K b - - 1 1")
    assert board.is_check("b")
    assert board.is_checkmate()
    assert not board.is_stalemate()


def test_stalemate_detection():
    # Classic king+pawn stalemate: black to move, not in check, no legal move.
    board = Board.from_fen("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    assert not board.is_check("b")
    assert board.is_stalemate()
    assert not board.is_checkmate()


def test_move_from_uci_rejects_illegal():
    board = Board.from_fen("6k1/5ppp/8/8/8/8/8/R6K w - - 0 1")
    # A pawn on a1? No - this is a rook. Moving it off-board style is illegal.
    try:
        move_from_uci(board, "a1a2")  # blocked? a2 is empty, this IS legal
    except ValueError:
        raise AssertionError("a1a2 should be legal")
    try:
        move_from_uci(board, "a1b3")  # rooks do not move diagonally
        raise AssertionError("a1b3 should be illegal")
    except ValueError:
        pass


def test_move_to_san_renders_mate_capture_castle_promotion():
    # Checkmate marker.
    assert san("6k1/5ppp/8/8/8/8/8/R6K w - - 0 1", "a1a8") == "Ra8#"
    # Capture.
    assert san("6k1/5ppp/3q4/8/8/8/5PPP/3R2K1 w - - 0 1", "d1d6") == "Rxd6"
    # Castling (both sides).
    assert san("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1g1") == "O-O"
    assert san("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "e1c1") == "O-O-O"
    # Promotion, with and without a resulting check.
    assert san("8/P7/8/8/8/8/8/k6K w - - 0 1", "a7a8n") == "a8=N"
    assert san("8/P7/8/8/8/8/8/k6K w - - 0 1", "a7a8q") == "a8=Q+"
    # Plain check marker.
    assert san("4k3/8/8/8/8/8/8/4R2K w - - 0 1", "e1e7") == "Re7+"


def test_move_to_san_disambiguates_by_file_then_rank():
    # Four knights; two (d5, f5) can reach e3, so a file hint is required.
    assert san("k7/8/8/3N1N2/8/3N1N2/8/K7 w - - 0 1", "d5e3") == "Nde3"


def test_ascii_render_contains_pieces_and_border():
    board = Board.from_fen("6k1/5ppp/8/8/8/8/8/R6K w - - 0 1")
    art = board.ascii()
    assert "k" in art and "R" in art
    assert "+------" in art
    assert "a b c d e f g h" in art
