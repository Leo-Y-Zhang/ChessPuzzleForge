import chess
from typing import Optional

# Piece values in centipawns (1 pawn = 100)
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

# Piece-square tables — bonuses for piece position (from white's perspective, a1=index 0)
# Encourages good piece placement: pawns push forward, knights prefer centre, etc.
PAWN_TABLE = [
     0,  0,  0,  0,  0,  0,  0,  0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
     5,  5, 10, 25, 25, 10,  5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5, -5,-10,  0,  0,-10, -5,  5,
     5, 10, 10,-20,-20, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0
]

KNIGHT_TABLE = [
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
]

BISHOP_TABLE = [
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
]

ROOK_TABLE = [
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10, 10, 10, 10, 10,  5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     0,  0,  0,  5,  5,  0,  0,  0
]

QUEEN_TABLE = [
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -10,  0,  5,  5,  5,  5,  0,-10,
     -5,  0,  5,  5,  5,  5,  0, -5,
      0,  0,  5,  5,  5,  5,  0, -5,
    -10,  5,  5,  5,  5,  5,  0,-10,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20
]

KING_TABLE = [
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -10,-20,-20,-20,-20,-20,-20,-10,
     20, 20,  0,  0,  0,  0, 20, 20,
     20, 30, 10,  0,  0, 10, 30, 20
]

TABLES = {
    chess.PAWN: PAWN_TABLE,
    chess.KNIGHT: KNIGHT_TABLE,
    chess.BISHOP: BISHOP_TABLE,
    chess.ROOK: ROOK_TABLE,
    chess.QUEEN: QUEEN_TABLE,
    chess.KING: KING_TABLE
}


def evaluate(board: chess.Board) -> int:
    """
    Score the position. Positive = good for white, negative = good for black.
    Combines material count with piece-square table bonuses.
    """
    if board.is_checkmate():
        # The side to move is in checkmate, so they lose
        return -20000 if board.turn == chess.WHITE else 20000
    if board.is_stalemate() or board.is_insufficient_material():
        return 0

    score = 0
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue

        value = PIECE_VALUES[piece.piece_type]
        table = TABLES[piece.piece_type]

        # Mirror the square index for black pieces so the table is always
        # read from that piece's own perspective (rank 1 = their back rank)
        if piece.color == chess.WHITE:
            pst_bonus = table[square]
        else:
            pst_bonus = table[chess.square_mirror(square)]

        if piece.color == chess.WHITE:
            score += value + pst_bonus
        else:
            score -= value + pst_bonus

    return score


def order_moves(board: chess.Board) -> list:
    """
    Sort moves so the most promising ones are searched first.
    This dramatically improves alpha-beta pruning efficiency — better moves
    are more likely to cause cutoffs early, pruning large parts of the tree.
    Priority: captures (MVV-LVA) > promotions > checks > quiet moves.
    """
    def move_priority(move):
        priority = 0
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            if victim and attacker:
                # MVV-LVA: capture high-value pieces with low-value pieces first
                priority += 10 * PIECE_VALUES[victim.piece_type] - PIECE_VALUES[attacker.piece_type]
        if move.promotion:
            priority += PIECE_VALUES[move.promotion]
        if board.gives_check(move):
            priority += 50
        return priority

    return sorted(board.legal_moves, key=move_priority, reverse=True)


def minimax(board: chess.Board, depth: int, alpha: int, beta: int, maximising: bool) -> int:
    """
    Minimax search with alpha-beta pruning.

    Alpha-beta pruning skips branches that cannot affect the final result.
    When we know the maximising player can already guarantee alpha, any branch
    where the minimising player can force below alpha gets cut — it will never
    be chosen. This reduces search from O(b^d) toward O(b^(d/2)) in the best case,
    effectively doubling the search depth for the same computation.
    """
    if depth == 0 or board.is_game_over():
        return evaluate(board)

    if maximising:
        max_eval = -float('inf')
        for move in order_moves(board):
            board.push(move)
            eval_score = minimax(board, depth - 1, alpha, beta, False)
            board.pop()
            max_eval = max(max_eval, eval_score)
            alpha = max(alpha, eval_score)
            if beta <= alpha:
                break  # Beta cutoff — minimiser already has a better option elsewhere
        return max_eval
    else:
        min_eval = float('inf')
        for move in order_moves(board):
            board.push(move)
            eval_score = minimax(board, depth - 1, alpha, beta, True)
            board.pop()
            min_eval = min(min_eval, eval_score)
            beta = min(beta, eval_score)
            if beta <= alpha:
                break  # Alpha cutoff — maximiser already has a better option elsewhere
        return min_eval


def best_move(board: chess.Board, depth: int = 3) -> Optional[chess.Move]:
    """
    Find the best move for the current player at the given search depth.
    Depth 3 = looks 3 half-moves ahead. Depth 4 is noticeably stronger but slower.
    """
    if board.is_game_over():
        return None

    best = None
    best_val = -float('inf') if board.turn == chess.WHITE else float('inf')

    for move in order_moves(board):
        board.push(move)
        val = minimax(board, depth - 1, -float('inf'), float('inf'),
                      board.turn == chess.WHITE)
        board.pop()

        if board.turn == chess.WHITE:
            if val > best_val:
                best_val = val
                best = move
        else:
            if val < best_val:
                best_val = val
                best = move

    return best
