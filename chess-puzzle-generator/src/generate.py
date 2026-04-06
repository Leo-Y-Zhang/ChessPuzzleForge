"""
generate.py — offline chess puzzle generator

How it works:
  1. Start from a set of standard opening positions (seed FENs)
  2. Play "realistic" games: engine moves with 30% randomness to get diverse positions
  3. At each position, check if there is a single clearly-best tactical move
  4. A position qualifies as a puzzle when one move beats all others by >150 centipawns
     AND leads to a decisive advantage (material gain or forced mate)
  5. Extract the full solution line, detect the theme, store in SQLite

This runs entirely offline — no internet required, no external data.

Usage:
    python generate.py            # generate 20 puzzles
    python generate.py --n 50     # generate 50 puzzles
    python generate.py --fen FEN  # check whether a specific FEN is a puzzle
"""
import chess
import random
import argparse
from typing import Optional

from engine import minimax, best_move, evaluate
from themes import detect_theme
from db import init_db, save_puzzle, count_puzzles

# Starting positions covering the main openings for diverse puzzle positions
SEED_FENS = [
    chess.STARTING_FEN,
    # After 1.e4 e5
    'rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',
    # After 1.d4 d5
    'rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 0 2',
    # Sicilian
    'rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',
    # French
    'rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',
    # Caro-Kann
    'rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2',
    # King's Indian setup
    'rnbqkb1r/pppppppp/5n2/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq - 1 2',
    # After 1.e4 c5 2.Nf3 d6 3.d4 cxd4 4.Nxd4 (Sicilian open)
    'rnbqkbnr/pp2pppp/3p4/8/3NP3/8/PPP2PPP/RNBQKB1R b KQkq - 0 5',
]


def _play_realistic_game(seed_fen: str, n_moves: int) -> chess.Board:
    """
    Play from seed_fen for n_moves half-moves.
    70% engine moves, 30% random non-blundering moves — creates varied middlegame positions.
    """
    board = chess.Board(seed_fen)
    for _ in range(n_moves):
        if board.is_game_over():
            break
        legal = list(board.legal_moves)
        if not legal:
            break
        if random.random() < 0.3:
            candidates = [m for m in legal if not _self_mates(board, m)]
            move = random.choice(candidates if candidates else legal)
        else:
            move = best_move(board, depth=2) or random.choice(legal)
        board.push(move)
    return board


def _self_mates(board: chess.Board, move: chess.Move) -> bool:
    """True if making this move immediately results in us being checkmated."""
    board.push(move)
    result = board.is_checkmate()
    board.pop()
    return result


def find_puzzle(board: chess.Board, depth: int = 3) -> tuple:
    """
    Determine whether this position is a good puzzle.

    A good puzzle has:
    - At least one legal move (non-trivial position)
    - Exactly one clearly best move: gap of >150cp between best and second-best
    - That best move leads to a decisive outcome: material win (>150cp) or forced mate

    Returns (is_puzzle, best_move, solution_line, score).
    """
    if board.is_game_over():
        return False, None, [], 0

    legal = list(board.legal_moves)
    if len(legal) < 2:
        return False, None, [], 0

    scored = []
    for move in legal:
        board.push(move)
        score = minimax(board, depth - 1, -float('inf'), float('inf'),
                        board.turn == chess.WHITE)
        board.pop()
        scored.append((move, score))

    # Sort from the perspective of the player to move
    reverse = (board.turn == chess.WHITE)
    scored.sort(key=lambda x: x[1], reverse=reverse)

    best_score = scored[0][1]
    second_score = scored[1][1]

    # Gap between best and second-best (always positive when there's a unique best)
    gap = abs(best_score - second_score)
    is_mate = abs(best_score) >= 19000
    is_material_win = (
        (board.turn == chess.WHITE and best_score > 150) or
        (board.turn == chess.BLACK and best_score < -150)
    )

    if gap < 150 or not (is_mate or is_material_win):
        return False, None, [], 0

    solution = _extract_solution(board, scored[0][0], depth)
    return True, scored[0][0], solution, best_score


def _extract_solution(board: chess.Board, first_move: chess.Move, depth: int) -> list:
    """
    Build the full solution line: [player_move, engine_response, player_move, ...].
    Follows forced moves up to `depth` half-moves deep.
    """
    solution = [first_move.uci()]
    board.push(first_move)

    if board.is_checkmate() or board.is_game_over():
        board.pop()
        return solution

    if depth >= 2:
        opp = best_move(board, depth=2)
        if opp:
            solution.append(opp.uci())
            board.push(opp)
            if not board.is_game_over() and depth >= 3:
                followup = best_move(board, depth=2)
                if followup:
                    solution.append(followup.uci())
                    board.push(followup)
                    if board.is_checkmate():
                        pass
                    board.pop()
            board.pop()

    board.pop()
    return solution


def _estimate_rating(theme: str, solution: list) -> int:
    """Rough difficulty rating based on theme and solution length."""
    base = {
        'mate_in_1': 700,
        'hanging_piece': 800,
        'back_rank': 900,
        'fork': 1000,
        'pin': 1100,
        'skewer': 1100,
        'discovered_attack': 1200,
        'mate_in_2': 1300,
        'mate_in_3': 1500,
        'tactics': 1000,
    }
    return base.get(theme, 1000) + max(0, len(solution) - 1) * 50


def generate_puzzles(n: int = 20, verbose: bool = True) -> int:
    """
    Generate up to n new puzzles and save them to the database.
    Returns the count of puzzles actually saved (skips duplicates).
    """
    init_db()
    generated = 0
    attempts = 0
    max_attempts = n * 40

    if verbose:
        print(f"Generating {n} puzzles (this may take a minute)...")

    while generated < n and attempts < max_attempts:
        attempts += 1
        seed = random.choice(SEED_FENS)
        board = _play_realistic_game(seed, n_moves=random.randint(6, 22))

        is_puzzle, move, solution, score = find_puzzle(board)
        if not is_puzzle:
            continue

        theme = detect_theme(board, solution)
        rating = _estimate_rating(theme, solution)

        if save_puzzle(fen=board.fen(), solution=solution, theme=theme, rating=rating):
            generated += 1
            if verbose:
                print(f"  [{generated}/{n}] {theme:20s}  rating ~{rating}  solution: {solution}")

    if verbose:
        total = count_puzzles()
        print(f"\nDone. {generated} new puzzles generated ({attempts} positions checked).")
        print(f"Database now contains {total} puzzles total.")

    return generated


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Offline chess puzzle generator')
    parser.add_argument('--n', type=int, default=20,
                        help='Number of puzzles to generate (default: 20)')
    parser.add_argument('--fen', type=str, default=None,
                        help='Check a specific FEN for puzzle quality')
    args = parser.parse_args()

    if args.fen:
        init_db()
        try:
            board = chess.Board(args.fen)
        except ValueError as e:
            print(f"Invalid FEN: {e}")
            raise SystemExit(1)
        is_puzzle, move, solution, score = find_puzzle(board)
        if is_puzzle:
            theme = detect_theme(board, solution)
            print(f"Puzzle found!  Theme: {theme}  Solution: {solution}  Score: {score}")
        else:
            print("No clear tactical puzzle found in this position.")
    else:
        generate_puzzles(n=args.n)
