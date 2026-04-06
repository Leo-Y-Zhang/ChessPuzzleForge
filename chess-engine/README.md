# Chess Engine

A chess engine built from scratch in Python with a playable web interface.

## What it does

- Full chess rules implementation (legal move generation, check/checkmate/stalemate detection)
- AI opponent using minimax algorithm with alpha-beta pruning
- Simple web UI to play against the engine in your browser

## Why I built it

Free chess engines exist, but almost none work fully offline — they depend on cloud servers or internet connections for their strongest play. I wanted to build an engine that runs entirely on-device, with no network dependency, so anyone can play strong chess anywhere. This also meant every part of the intelligence had to be self-contained: no API calls, no remote evaluation, just pure local computation.

## Technical Decisions

### Why alpha-beta pruning?
Naive minimax evaluates every possible position. Alpha-beta pruning cuts branches that can't affect the final decision, making the same search roughly 10x faster. This was the key algorithmic challenge.

### Why Python?
Readable, fast to prototype, strong chess libraries available (python-chess) if needed for validation.

## How to run

```bash
# Install dependencies
pip install -r requirements.txt

# Run the web server
python src/app.py

# Open http://localhost:5000 in your browser
```

## Project structure

```
chess-engine/
├── src/
│   ├── engine.py        # Core minimax + alpha-beta logic
│   ├── board.py         # Board representation and move generation
│   ├── evaluate.py      # Position evaluation function
│   └── app.py           # Flask web server
├── tests/
│   └── test_engine.py   # Unit tests for move generation and evaluation
├── docs/
│   ├── devlog.md        # Engineering logbook
│   └── writeup.md       # Personal statement material
└── README.md
```

## What I'd improve next

- Add an opening book (precomputed best opening moves for the first ~10 moves)
- Add an endgame table for common K+R vs K, K+Q vs K positions

## What I learned

[Fill this in as you build — what surprised you, what was harder than expected]
