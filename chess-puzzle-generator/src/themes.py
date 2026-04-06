"""
themes.py — tactical theme detection for generated chess puzzles.

Detects the primary theme by analysing the solution line:
  mate_in_1, mate_in_2, mate_in_3, fork, pin, skewer,
  back_rank, discovered_attack, hanging_piece, tactics (catch-all)
"""
import chess
from typing import List
from engine import PIECE_VALUES


def detect_theme(board: chess.Board, solution: List[str]) -> str:
    """
    Identify the primary tactical theme.
    board  — position BEFORE any solution moves are played
    solution — list of UCI strings (full solution line)
    """
    if not solution:
        return 'tactics'

    first = chess.Move.from_uci(solution[0])

    # ── Checkmate themes ──────────────────────────────────────────────────────
    board.push(first)
    if board.is_checkmate():
        board.pop()
        return 'mate_in_1'
    board.pop()

    if len(solution) >= 3:
        b = board.copy()
        for i, uci in enumerate(solution):
            b.push(chess.Move.from_uci(uci))
            if b.is_checkmate():
                # Number of player moves = ceil of (index+1 / 2)
                n = (i // 2) + 1
                return f'mate_in_{n}'

    # ── Positional / tactical themes ─────────────────────────────────────────
    if _is_fork(board, first):
        return 'fork'
    if _is_discovered_attack(board, first):
        return 'discovered_attack'
    if _is_back_rank_mate(board, first):
        return 'back_rank'
    if _is_skewer(board, first):
        return 'skewer'
    if _is_pin(board, first):
        return 'pin'
    if _is_free_capture(board, first):
        return 'hanging_piece'

    return 'tactics'


# ── Individual theme detectors ────────────────────────────────────────────────

def _is_fork(board: chess.Board, move: chess.Move) -> bool:
    """After the move, does the piece simultaneously attack 2+ valuable enemy pieces?"""
    board.push(move)
    piece = board.piece_at(move.to_square)
    if piece is None:
        board.pop()
        return False
    attacked = sum(
        1 for sq in chess.SQUARES
        if (v := board.piece_at(sq)) is not None
        and v.color != piece.color
        and v.piece_type in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT, chess.KING)
        and sq in board.attacks(move.to_square)
    )
    board.pop()
    return attacked >= 2


def _is_discovered_attack(board: chess.Board, move: chess.Move) -> bool:
    """Does moving this piece expose a new attack from a piece behind it?"""
    moving = board.piece_at(move.from_square)
    if moving is None:
        return False
    color = moving.color
    enemy = not color

    def attacked_squares(b):
        return {
            sq for sq in chess.SQUARES
            if (v := b.piece_at(sq)) is not None
            and v.color == enemy
            and v.piece_type not in (chess.PAWN, chess.KING)
            and b.is_attacked_by(color, sq)
        }

    before = attacked_squares(board)
    board.push(move)
    after = attacked_squares(board)
    # New attacks that aren't from the moved piece itself
    # board.attacks() returns SquareSet — convert to set for subtraction
    new = after - before - set(board.attacks(move.to_square))
    board.pop()
    return bool(new)


def _is_back_rank_mate(board: chess.Board, move: chess.Move) -> bool:
    """Is the move a back-rank (first/last rank) checkmate?"""
    board.push(move)
    if board.is_checkmate():
        rank = chess.square_rank(move.to_square)
        piece = board.piece_at(move.to_square)
        result = piece is not None and (
            (piece.color == chess.WHITE and rank == 7) or
            (piece.color == chess.BLACK and rank == 0)
        )
        board.pop()
        return result
    board.pop()
    return False


def _is_skewer(board: chess.Board, move: chess.Move) -> bool:
    """
    After the move, does a slider (Q/R/B) attack a high-value piece with a
    lower-value piece sitting behind it on the same ray?
    """
    moving = board.piece_at(move.from_square)
    if moving is None or moving.piece_type not in (chess.QUEEN, chess.ROOK, chess.BISHOP):
        return False

    board.push(move)
    attacker = board.piece_at(move.to_square)
    if attacker is None:
        board.pop()
        return False

    attacker_val = PIECE_VALUES.get(attacker.piece_type, 0)

    for sq in chess.SQUARES:
        victim = board.piece_at(sq)
        if victim and victim.color != attacker.color and sq in board.attacks(move.to_square):
            victim_val = PIECE_VALUES.get(victim.piece_type, 0)
            # Skewer: we're hitting something at least as valuable as us
            if victim_val >= attacker_val:
                board.pop()
                return True

    board.pop()
    return False


def _is_pin(board: chess.Board, move: chess.Move) -> bool:
    """Does the move create a new absolute pin on an enemy piece?"""
    moving = board.piece_at(move.from_square)
    if moving is None or moving.piece_type not in (chess.QUEEN, chess.ROOK, chess.BISHOP):
        return False

    board.push(move)
    enemy = not moving.color
    pinned = any(
        board.is_pinned(enemy, sq)
        for sq in chess.SQUARES
        if (p := board.piece_at(sq)) is not None
        and p.color == enemy
        and p.piece_type != chess.KING
    )
    board.pop()
    return pinned


def _is_free_capture(board: chess.Board, move: chess.Move) -> bool:
    """Does the move capture an undefended piece (winning material for free)?"""
    if not board.is_capture(move):
        return False
    captured = board.piece_at(move.to_square)
    if captured is None:
        return False
    board.push(move)
    our_piece = board.piece_at(move.to_square)
    # If the capturing piece is not now attacked, it was a free capture
    is_free = our_piece is not None and not board.is_attacked_by(not our_piece.color, move.to_square)
    board.pop()
    return is_free
