from flask import Flask, jsonify, send_from_directory
from analyse import get_stats

app = Flask(__name__, static_folder='static')


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/api/stats')
def stats():
    return jsonify(get_stats())


if __name__ == '__main__':
    print("Chess analyser running at http://localhost:5001")
    print("Make sure you've run fetch.py first to load your games.")
    app.run(debug=False, port=5001)
