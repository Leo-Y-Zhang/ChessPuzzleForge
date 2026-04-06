# Chess Puzzle Generator

An offline tactical puzzle trainer that generates its own puzzles using a chess engine — no internet, no external puzzle databases.

## What it does

- Generates chess puzzles from scratch using minimax search: finds positions where one move is clearly best
- Detects tactical themes automatically: mate in 1/2/3, fork, pin, skewer, back rank, discovered attack
- Stores puzzles in a local SQLite database so generation only needs to happen once
- Tracks your solve history and progress
- Web UI lets you attempt puzzles interactively with instant feedback

## Why I built it

Most puzzle trainers pull from online databases (Lichess puzzles, Chess Tempo) and need a live internet connection. I wanted something that runs completely offline — one that also lets me understand how puzzles are found algorithmically. The interesting question was: how do you write code that can tell the difference between a "good puzzle" position and a random one?

## Technical Decisions

### How puzzle detection works
A position qualifies as a puzzle when:
1. There is exactly one move that is significantly better than all others (>150 centipawn gap)
2. That best move leads to a decisive advantage: either material gain or forced checkmate

This is evaluated by running minimax search on every legal move and comparing the top two scores. If the gap is large enough and the outcome decisive, the position is saved as a puzzle.

### Why generate positions from openings?
Starting from known opening positions and playing semi-random moves produces realistic middlegames with plausible piece placement — far more likely to contain genuine tactics than fully random positions, which tend to be unrealistic.

### Why SQLite?
Puzzle generation is slow (the engine searches thousands of positions). Running once and caching means the trainer loads instantly on subsequent uses.

### Why offline?
The same constraint that motivated the chess engine: the whole system should work anywhere, with no network dependency.

## How to run

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server (generates 20 starter puzzles automatically on first run)
python src/app.py

# Open http://localhost:5002
```

To generate more puzzles manually:

```bash
python src/generate.py --n 50   # generate 50 more puzzles
python src/generate.py --fen "FEN_STRING"  # check a specific position
```

## Project structure

```
chess-puzzle-generator/
├── src/
│   ├── generate.py      # Puzzle generation: position search + quality filter
│   ├── themes.py        # Tactical theme detection (fork, pin, mate, etc.)
│   ├── engine.py        # Minimax + alpha-beta (self-contained, offline)
│   ├── db.py            # SQLite: puzzles + solve history
│   ├── app.py           # Flask web server
│   └── static/
│       └── index.html   # Interactive puzzle UI
├── tests/
│   └── test_puzzles.py
├── data/                # puzzles.db lives here (auto-created, git-ignored)
├── docs/
│   ├── devlog.md
│   └── writeup.md
└── README.md
```

## API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/puzzle/next` | Next unsolved puzzle (optionally `?theme=fork`) |
| POST | `/api/puzzle/<id>/check` | Verify a player's move |
| GET | `/api/puzzle/<id>/solution` | Reveal the full solution |
| GET | `/api/stats` | Puzzle count and progress stats |
| GET | `/api/themes` | Available themes and counts |
| POST | `/api/generate` | Generate more puzzles on demand |

## Running the tests

```bash
pytest tests/
```

## What I'd improve next

- Improve position diversity by using a wider opening book
- Add an Elo-style rating system that adjusts based on solve time
- Support multi-move puzzles where the opponent has multiple defences (solution trees rather than lines)

## What I learned

[Fill this in as you build]
