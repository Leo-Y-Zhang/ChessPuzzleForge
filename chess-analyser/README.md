# Chess Game Analyser

A personal stats dashboard that pulls your games from Chess.com and Lichess and visualises patterns in your play.

## What it does

- Fetches your game history via Chess.com and Lichess public APIs
- Analyses patterns: win rate by opening, accuracy over time, most common blunders, performance by time control
- Displays everything in a clean web dashboard with charts
- Runs fully locally — data is cached so it works offline after first fetch

## Why I built it

Existing stats tools show you numbers but don't let you dig into your own patterns in a custom way. I wanted to build something tailored to the questions I actually care about as a player — and learn how to work with real APIs and data pipelines in the process.

## Technical Decisions

### Why cache locally?
After the first API pull, all data is stored in a local SQLite database. This means the dashboard works offline and doesn't hammer the APIs on every load.

### Why Flask + Chart.js?
Lightweight backend, minimal frontend dependency. Keeps the stack simple enough to understand fully.

## How to run

```bash
# Install dependencies
pip install -r requirements.txt

# Fetch your games (run once, then cached)
python src/fetch.py --username YOUR_USERNAME --platform lichess

# Start the dashboard
python src/app.py

# Open http://localhost:5000
```

## Project structure

```
chess-analyser/
├── src/
│   ├── fetch.py         # API fetcher — Chess.com and Lichess
│   ├── analyse.py       # Stats and pattern analysis
│   ├── app.py           # Flask web server + routes
│   └── db.py            # SQLite database layer
├── tests/
│   └── test_analyse.py  # Unit tests for analysis logic
├── docs/
│   ├── devlog.md        # Engineering logbook
│   └── writeup.md       # Personal statement material
└── README.md
```

## What I'd improve next

- Add opening tree visualisation (where do my games diverge from theory?)
- Export a PDF report of your stats
- Compare your stats against players at a similar rating

## What I learned

[Fill this in as you build]
