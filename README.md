# Chess Projects — UCAS Portfolio

Three projects built to demonstrate CS knowledge and genuine interest for university applications. All run fully offline.

## Projects

| Project | Description | Port |
|---|---|---|
| [chess-engine](./chess-engine/) | Chess engine with minimax + alpha-beta pruning, playable in your browser | 5000 |
| [chess-analyser](./chess-analyser/) | Personal game stats dashboard — pulls from Chess.com / Lichess, works offline after first fetch | 5001 |
| [chess-puzzle-generator](./chess-puzzle-generator/) | Generates tactical puzzles using the engine itself, stores them locally, lets you train offline | 5002 |

## Quick start

Each project is independent. Navigate into the folder and follow its README.

```bash
# Chess Engine
cd chess-engine
pip install -r requirements.txt
python src/app.py          # → http://localhost:5000

# Chess Analyser
cd chess-analyser
pip install -r requirements.txt
python src/fetch.py lichess YOUR_USERNAME   # fetch games once
python src/app.py          # → http://localhost:5001

# Puzzle Generator
cd chess-puzzle-generator
pip install -r requirements.txt
python src/app.py          # generates starter puzzles then → http://localhost:5002
```

## Running the tests

```bash
# From inside each project directory:
pytest tests/
```

## Purpose

These projects demonstrate:
- Algorithm design: minimax, alpha-beta pruning, recursive search, heuristics
- Data pipelines: API integration, local caching, SQLite
- Software design: self-contained systems with no network dependency at runtime
- Web development: Flask backends, JavaScript frontends, REST APIs

## Skills demonstrated

Python · JavaScript · Flask · SQLite · REST APIs · algorithm design · git
