from flask import Flask, request, jsonify, send_from_directory
import chess
from engine import best_move
import os

app = Flask(__name__, static_folder='static')

# Single board + engine-colour state (local single-player app)
board = chess.Board()
engine_color = chess.BLACK  # Default: engine plays black, you play white


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/new', methods=['POST'])
def new_game():
    global board, engine_color
    data = request.get_json(silent=True) or {}
    board = chess.Board()

    player_color = data.get('player_color', 'white')
    engine_color = chess.BLACK if player_color == 'white' else chess.WHITE

    response = {'fen': board.fen(), 'player_color': player_color}

    # If player chose black, engine makes the first move immediately
    if engine_color == chess.WHITE:
        depth = int(data.get('depth', 3))
        move = best_move(board, depth=depth)
        if move:
            board.push(move)
            response['engine_move'] = move.uci()
            response['fen'] = board.fen()

    return jsonify(response)


@app.route('/move', methods=['POST'])
def player_move():
    global board
    data = request.get_json(silent=True) or {}
    uci = data.get('move', '')
    depth = int(data.get('depth', 3))

    try:
        move = chess.Move.from_uci(uci)
    except ValueError:
        return jsonify({'error': 'invalid move format'}), 400

    if move not in board.legal_moves:
        return jsonify({'error': 'illegal move'}), 400

    board.push(move)

    if board.is_game_over():
        return jsonify({
            'fen': board.fen(),
            'game_over': True,
            'result': _result_text(board),
            'material': _material_balance(board)
        })

    engine_move = best_move(board, depth=depth)
    if engine_move:
        board.push(engine_move)

    return jsonify({
        'fen': board.fen(),
        'engine_move': engine_move.uci() if engine_move else None,
        'game_over': board.is_game_over(),
        'result': _result_text(board) if board.is_game_over() else None,
        'in_check': board.is_check(),
        'material': _material_balance(board)
    })


def _result_text(board: chess.Board) -> str:
    if board.is_checkmate():
        winner = 'Black' if board.turn == chess.WHITE else 'White'
        return f'Checkmate — {winner} wins'
    if board.is_stalemate():
        return 'Stalemate — Draw'
    if board.is_insufficient_material():
        return 'Insufficient material — Draw'
    if board.is_seventyfive_moves():
        return '75-move rule — Draw'
    if board.is_fivefold_repetition():
        return 'Fivefold repetition — Draw'
    return board.result()


def _material_balance(board: chess.Board) -> dict:
    """Return piece counts for both sides for the material display."""
    values = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
              chess.ROOK: 5, chess.QUEEN: 9}
    white_score = black_score = 0
    for sq in chess.SQUARES:
        piece = board.piece_at(sq)
        if piece and piece.piece_type in values:
            if piece.color == chess.WHITE:
                white_score += values[piece.piece_type]
            else:
                black_score += values[piece.piece_type]
    return {
        'white': white_score,
        'black': black_score,
        'advantage': white_score - black_score
    }


if __name__ == '__main__':
    print("Chess engine running at http://localhost:5000")
    print("No internet required — fully offline.")
    app.run(debug=False, port=5000)
