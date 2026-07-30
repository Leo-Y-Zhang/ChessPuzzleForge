"""Mine engine-verified puzzles from the mainlines of a PGN game corpus.

Pipeline: each game is replayed through ``parse_san`` (an illegal game score
fails loud); at every position along the mainline, cheap prefilters decide
which of the expensive searches are worth running (the mate-in-1 scan,
``forced_mate_move`` at depths 2-3, ``find_forks``). Candidates are deduped by
position and re-verified through :func:`palamedes.verifier.verify_puzzle`
before they are emitted - a mined answer is proven, never assumed.

Honesty notes:

* **Recall is best-effort by design**; soundness is not. The prefilters trade
  recall for speed (deep mate searches only run where a check is available -
  and, for depth 3, only in positions of at most ``_M3_MAX_MEN`` men - so a
  quiet-first-move mate in a heavy middlegame will be missed), and only the
  mainline is replayed. Everything that IS emitted has been re-proven.
* A fork is emitted as a ``win_material`` puzzle only when the verifier's
  strict recapture model can prove the gain (at least
  ``_MIN_FORK_THRESHOLD`` pawns); forks whose payoff needs a follow-up move
  the model cannot see are found by ``find_forks`` but not emitted.
* Output is deterministic: discovery order (game order, then ply order), with
  one puzzle at most per distinct position.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from .engine import (
    Board,
    Move,
    forced_mate_move,
    move_to_san,
    parse_san,
    parse_square,
    piece_color,
)
from .fen_bank import Puzzle
from .pgn import PgnError, PgnGame, read_games
from .tactics import find_forks
from .verifier import PIECE_VALUES, net_material_gain, verify_puzzle

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

# Prefilter thresholds (the leverage that keeps pure-Python mining fast).
_MATE_MATERIAL_MIN = 5.0  # at least a rook's worth; a 7th-rank pawn counts as a queen
_M2_SMALL_POSITION_MEN = 8  # depth-2 search always runs in positions this small...
_M2_FORCING_REPLY_MAX = 4  # ...or when some check leaves the defender <= this many replies
_M3_MAX_MEN = 6  # depth-3 search only in heavily simplified positions

_MIN_FORK_THRESHOLD = 1.0  # a fork must prove at least a pawn under the recapture model

_PIECE_NAMES = {"P": "pawn", "N": "knight", "B": "bishop", "R": "rook", "Q": "queen"}

Progress = Callable[[str], None]


def _mating_material(board: Board) -> float:
    """Material of the side to move, counting a pawn on its 7th rank as a queen."""
    total = 0.0
    for sq in range(64):
        piece = board.piece_at(sq)
        if piece is None or piece_color(piece) != board.turn:
            continue
        rank = sq // 8
        if piece == "P" and rank == 6 or piece == "p" and rank == 1:
            total += PIECE_VALUES["Q"]
        else:
            total += PIECE_VALUES[piece.upper()]
    return total


def _men_on_board(board: Board) -> int:
    return sum(1 for sq in range(64) if board.piece_at(sq) is not None)


def _defender_has_forkable_piece(board: Board) -> bool:
    """True if the opponent owns a non-king piece worth at least a knight."""
    return any(
        piece is not None
        and piece_color(piece) != board.turn
        and PIECE_VALUES[piece.upper()] >= 3.0
        for piece in (board.piece_at(sq) for sq in range(64))
    )


def _emit(puzzle: Puzzle, out: list[Puzzle]) -> None:
    """Re-verify a mined candidate with the existing verifier, then emit it."""
    ok, message = verify_puzzle(puzzle)
    if not ok:
        raise AssertionError(f"mined candidate {puzzle['id']} failed verification: {message}")
    out.append(puzzle)


def _mine_mate(board: Board, puzzle_id: str, out: list[Puzzle]) -> bool:
    """Run the prefiltered mate searches on ``board``; True if a puzzle was emitted."""
    fen = board.to_fen()
    moves = board.legal_moves()
    if not moves:
        return False  # the game just ended here (mate/stalemate)

    # One push per move; a mate in 1 is a checking move with no replies.
    checking: list[tuple[Move, Board]] = []
    for move in moves:
        child = board.push(move)
        if child.is_check():
            checking.append((move, child))
    mate1: list[Move] = []
    reply_counts: list[int] = []
    for move, child in checking:
        replies = child.legal_moves()
        if replies:
            reply_counts.append(len(replies))
        else:
            mate1.append(move)

    if mate1:
        puzzle: Puzzle = {
            "id": f"{puzzle_id}-m1",
            "fen": fen,
            "goal": "mate_in_1",
            "solution": [m.uci() for m in mate1],
            "san": ", ".join(move_to_san(board, m) for m in mate1),
            "theme": "mined mate-in-one",
        }
        _emit(puzzle, out)
        return True

    if not checking or _mating_material(board) < _MATE_MATERIAL_MIN:
        return False
    men = _men_on_board(board)

    forcing = men <= _M2_SMALL_POSITION_MEN or any(
        n <= _M2_FORCING_REPLY_MAX for n in reply_counts
    )
    if forcing:
        key = forced_mate_move(board, 2)
        if key is not None:
            puzzle = {
                "id": f"{puzzle_id}-m2",
                "fen": fen,
                "goal": "mate_in_2",
                "solution": [key],
                "san": f"{move_to_san(board, _move_by_uci(moves, key))} (then mate next move)",
                "theme": "mined mate-in-two",
            }
            _emit(puzzle, out)
            return True

    if men <= _M3_MAX_MEN:
        key = forced_mate_move(board, 3)
        if key is not None:
            puzzle = {
                "id": f"{puzzle_id}-m3",
                "fen": fen,
                "goal": "mate_in_3",
                "solution": [key],
                "san": f"{move_to_san(board, _move_by_uci(moves, key))} (then mate within three)",
                "theme": "mined mate-in-three",
            }
            _emit(puzzle, out)
            return True
    return False


def _move_by_uci(moves: Sequence[Move], uci: str) -> Move:
    for move in moves:
        if move.uci() == uci:
            return move
    raise AssertionError(f"search returned a move not in the legal list: {uci}")


def _mine_fork(board: Board, puzzle_id: str, out: list[Puzzle]) -> bool:
    """Emit the best fork the verifier's recapture model can prove, if any."""
    if not _defender_has_forkable_piece(board):
        return False
    candidates: list[tuple[float, str, str]] = []
    for fork in find_forks(board):
        gain = net_material_gain(board, fork.uci)
        if gain >= _MIN_FORK_THRESHOLD:
            candidates.append((gain, fork.uci, fork.san))
    if not candidates:
        return False
    gain, uci, san = max(candidates, key=lambda c: (c[0], c[1]))
    mover = board.piece_at(parse_square(uci[:2]))
    name = _PIECE_NAMES.get("?" if mover is None else mover.upper(), "piece")
    puzzle: Puzzle = {
        "id": f"{puzzle_id}-fork",
        "fen": board.to_fen(),
        "goal": "win_material",
        "solution": [uci],
        "san": san,
        "threshold": gain,
        "theme": f"mined {name} fork",
    }
    _emit(puzzle, out)
    return True


def _start_board(game: PgnGame) -> Board:
    """The game's initial position: its FEN tag when present, else the start position."""
    fen = game.tags.get("FEN")
    if fen is None:
        return Board.from_fen(START_FEN)
    try:
        return Board.from_fen(fen)
    except ValueError as exc:
        raise PgnError(f"game {game.game_number}: invalid FEN tag: {exc}") from None


def mine_games(
    games: Sequence[PgnGame],
    max_games: int | None = None,
    max_plies: int | None = None,
    progress: Progress | None = None,
) -> list[Puzzle]:
    """Mine verified puzzles from parsed games; deterministic discovery order.

    ``max_games`` bounds how many games are mined; ``max_plies`` bounds how many
    plies of each game are replayed. Raises :class:`PgnError` when a game's
    mainline contains an illegal or unparsable move (fail loud, never guess).
    """
    if max_games is not None and max_games < 0:
        raise ValueError(f"max_games must be >= 0, got {max_games}")
    if max_plies is not None and max_plies < 0:
        raise ValueError(f"max_plies must be >= 0, got {max_plies}")

    mined: list[Puzzle] = []
    seen_positions: set[str] = set()
    pool = list(games)[: len(games) if max_games is None else max_games]
    for game in pool:
        board = _start_board(game)
        found_before = len(mined)
        plies = game.moves[: len(game.moves) if max_plies is None else max_plies]
        for ply, san in enumerate(plies):
            _scan(board, game.game_number, ply, seen_positions, mined)
            try:
                move = parse_san(board, san)
            except ValueError as exc:
                raise PgnError(
                    f"game {game.game_number}: move {ply + 1} ({san!r}) "
                    f"does not name a legal move: {exc}"
                ) from None
            board = board.push(move)
        _scan(board, game.game_number, len(plies), seen_positions, mined)
        if progress is not None:
            progress(
                f"game {game.game_number}/{len(pool)}: replayed {len(plies)} plies, "
                f"{len(mined) - found_before} new puzzles ({len(mined)} total)"
            )
    return mined


def _scan(
    board: Board, game_number: int, ply: int, seen_positions: set[str], out: list[Puzzle]
) -> None:
    """Scan one position: dedupe, prefilter, search, verify, emit."""
    key = " ".join(board.to_fen().split()[:4])  # ignore move counters for dedupe
    if key in seen_positions:
        return
    seen_positions.add(key)
    puzzle_id = f"mined-g{game_number}-p{ply}"
    if _mine_mate(board, puzzle_id, out):
        return
    _mine_fork(board, puzzle_id, out)


def mine_pgn(
    text: str,
    max_games: int | None = None,
    max_plies: int | None = None,
    progress: Progress | None = None,
) -> list[Puzzle]:
    """Parse ``text`` as PGN and mine it; see :func:`mine_games`."""
    return mine_games(read_games(text), max_games, max_plies, progress)
