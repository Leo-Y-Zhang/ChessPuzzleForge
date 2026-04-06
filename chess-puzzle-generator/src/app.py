"""
app.py — Flask web server for the offline chess puzzle trainer.

Routes:
  GET  /                          → puzzle UI
  GET  /api/puzzle?theme=X        → random puzzle (metadata only, no solution)
  GET  /api/puzzle/next?theme=X   → next unsolved puzzle
  POST /api/puzzle/<id>/check     → verify a player's move
  GET  /api/puzzle/<id>/solution  → reveal solution (counts as failed attempt)
  GET  /api/stats                 → puzzle + progress stats
  GET  /api/themes                → list of available themes
  POST /api/generate              → generate more puzzles (runs engine offline)

Run:
    python src/app.py
    open http://localhost:5002
"""
import sys
import os
import chess
from flask import Flask, request, jsonify, send_from_directory

from db import (
    init_db, get_random_puzzle, get_next_unsolved, get_puzzle,
    record_attempt, get_stats, count_puzzles, get_connection
)

app = Flask(__name__, static_folder='static')


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


# ── Puzzle retrieval ──────────────────────────────────────────────────────────

@app.route('/api/puzzle')
def random_puzzle():
    theme = request.args.get('theme')
    puzzle = get_random_puzzle(theme)
    return _puzzle_response(puzzle)


@app.route('/api/puzzle/next')
def next_puzzle():
    theme = request.args.get('theme')
    puzzle = get_next_unsolved(theme)
    return _puzzle_response(puzzle)


def _puzzle_response(puzzle):
    if puzzle is None:
        return jsonify({'error': 'No puzzles found. Run generate.py first.'}), 404
    board = chess.Board(puzzle['fen'])
    return jsonify({
        'id': puzzle['id'],
        'fen': puzzle['fen'],
        'theme': puzzle['theme'],
        'rating': puzzle['rating'],
        'to_move': 'White' if board.turn == chess.WHITE else 'Black',
    })


# ── Move checking ─────────────────────────────────────────────────────────────

@app.route('/api/puzzle/<int:puzzle_id>/check', methods=['POST'])
def check_move(puzzle_id):
    """
    Verify the player's move against the solution.

    Request JSON:
        { "move": "e2e4", "move_index": 0 }

    move_index is the index into the solution array. Player moves are at even
    indices (0, 2, 4 ...). The server never sends engine moves to the client
    before they are needed, so the solution stays hidden until revealed.

    Response on correct move (not yet complete):
        { "correct": true, "complete": false,
          "opponent_move": "d8h4", "next_move_index": 2 }

    Response on completion:
        { "correct": true, "complete": true }
    """
    puzzle = get_puzzle(puzzle_id)
    if not puzzle:
        return jsonify({'error': 'Puzzle not found'}), 404

    data = request.get_json(silent=True) or {}
    move_uci = data.get('move', '')
    move_index = int(data.get('move_index', 0))
    solution = puzzle['solution']

    if move_index >= len(solution):
        return jsonify({'error': 'Invalid move index'}), 400

    expected = solution[move_index]
    # Accept move regardless of promotion piece choice (first 4 chars must match)
    correct = move_uci == expected or move_uci[:4] == expected[:4]

    if not correct:
        return jsonify({'correct': False, 'complete': False})

    next_index = move_index + 1
    if next_index >= len(solution):
        record_attempt(puzzle_id, solved=True)
        return jsonify({'correct': True, 'complete': True})

    # Opponent's response is the next move in the solution
    opponent_move = solution[next_index]
    next_player_index = next_index + 1

    if next_player_index >= len(solution):
        # Opponent's response is the last move — puzzle complete after it's shown
        record_attempt(puzzle_id, solved=True)
        return jsonify({
            'correct': True,
            'complete': True,
            'opponent_move': opponent_move,
        })

    return jsonify({
        'correct': True,
        'complete': False,
        'opponent_move': opponent_move,
        'next_move_index': next_player_index,
    })


@app.route('/api/puzzle/<int:puzzle_id>/solution')
def reveal_solution(puzzle_id):
    puzzle = get_puzzle(puzzle_id)
    if not puzzle:
        return jsonify({'error': 'Not found'}), 404
    record_attempt(puzzle_id, solved=False)
    return jsonify({'solution': puzzle['solution']})


# ── Stats & metadata ──────────────────────────────────────────────────────────

@app.route('/api/stats')
def stats():
    return jsonify(get_stats())


@app.route('/api/themes')
def themes():
    conn = get_connection()
    rows = conn.execute(
        'SELECT theme, COUNT(*) as n FROM puzzles GROUP BY theme ORDER BY n DESC'
    ).fetchall()
    conn.close()
    return jsonify([{'theme': r[0], 'count': r[1]} for r in rows])


# ── On-demand generation ──────────────────────────────────────────────────────

@app.route('/api/generate', methods=['POST'])
def generate():
    """Generate more puzzles on demand (runs entirely offline)."""
    data = request.get_json(silent=True) or {}
    n = min(int(data.get('n', 20)), 100)  # Cap at 100 per request
    from generate import generate_puzzles
    count = generate_puzzles(n=n, verbose=False)
    total = count_puzzles()
    return jsonify({'generated': count, 'total': total})


# ── Startup ───────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    n = count_puzzles()
    if n == 0:
        print("No puzzles found — generating 20 starter puzzles (this takes ~30 seconds)...")
        from generate import generate_puzzles
        generate_puzzles(n=20)
        n = count_puzzles()
    print(f"Chess Puzzle Trainer — {n} puzzles loaded")
    print("Running at http://localhost:5002  (fully offline, no internet needed)")
    app.run(debug=False, port=5002)
