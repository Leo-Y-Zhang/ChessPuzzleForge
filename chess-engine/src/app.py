from flask import Flask, request, jsonify, send_from_directory
import chess
from engine import best_move
import os

app = Flask(__name__, static_folder='static')

# Single board instance — this is a local offline app so one game at a time is fine
board = chess.Board()


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/new', methods=['POST'])
def new_game():
    global board
    board = chess.Board()
    return jsonify({'fen': board.fen()})


@app.route('/move', methods=['POST'])
def player_move():
    global board
    data = request.json
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
            'result': _result_text(board)
        })

    # Engine responds as black
    engine_move = best_move(board, depth=depth)
    if engine_move:
        board.push(engine_move)

    return jsonify({
        'fen': board.fen(),
        'engine_move': engine_move.uci() if engine_move else None,
        'game_over': board.is_game_over(),
        'result': _result_text(board) if board.is_game_over() else None,
        'in_check': board.is_check()
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


if __name__ == '__main__':
    print("Chess engine running at http://localhost:5000")
    print("No internet required — fully offline.")
    app.run(debug=False, port=5000)
