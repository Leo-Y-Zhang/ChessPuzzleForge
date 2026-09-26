"""A small, self-contained chess engine (pure Python standard library only).

This module implements just enough of the rules of chess to:

* parse a position from FEN,
* render it as ASCII,
* generate all *legal* moves for the side to move,
* detect check and checkmate,
* solve / verify forced mates ("mate in N").

It intentionally depends on nothing outside the standard library so that the
project's core logic (and its unit tests) work even when the optional
``python-chess`` package is not installed.  When ``python-chess`` *is*
installed it is used only by the optional cross-check tests to independently
confirm that this engine agrees with a reference implementation.

Board / square convention
--------------------------
Squares are integers 0..63 where ``index = rank * 8 + file``:

* ``file`` 0..7 maps to files ``a``..``h``
* ``rank`` 0..7 maps to ranks ``1``..``8``

So a1 == 0, h1 == 7, a8 == 56, h8 == 63.  White pieces are uppercase letters
(``PNBRQK``), black pieces are lowercase (``pnbrqk``).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

WHITE = "w"
BLACK = "b"

# Movement offsets expressed as (file_delta, rank_delta).
_KNIGHT_DELTAS = [(1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2)]
_KING_DELTAS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
_BISHOP_DIRS = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
_ROOK_DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]
_QUEEN_DIRS = _BISHOP_DIRS + _ROOK_DIRS


def square(file: int, rank: int) -> int:
    return rank * 8 + file


def file_of(sq: int) -> int:
    return sq % 8


def rank_of(sq: int) -> int:
    return sq // 8


def square_name(sq: int) -> str:
    return "abcdefgh"[file_of(sq)] + str(rank_of(sq) + 1)


def parse_square(name: str) -> int:
    name = name.strip()
    if len(name) != 2 or name[0] not in "abcdefgh" or name[1] not in "12345678":
        raise ValueError(f"invalid square name: {name!r}")
    return square("abcdefgh".index(name[0]), int(name[1]) - 1)


def _on_board(file: int, rank: int) -> bool:
    return 0 <= file <= 7 and 0 <= rank <= 7


def piece_color(piece: str) -> str:
    return WHITE if piece.isupper() else BLACK


@dataclass(frozen=True)
class Move:
    """A single move in the game.

    ``promotion`` is a lowercase piece letter (``q``/``r``/``b``/``n``) or None.
    ``is_ep`` marks an en-passant capture, ``is_castle`` a castling move.
    """

    from_sq: int
    to_sq: int
    promotion: str | None = None
    is_ep: bool = False
    is_castle: bool = False

    def uci(self) -> str:
        s = square_name(self.from_sq) + square_name(self.to_sq)
        if self.promotion:
            s += self.promotion
        return s

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.uci()


class Board:
    """An immutable-ish chess position.  ``push`` returns a *new* Board."""

    __slots__ = ("squares", "turn", "castling", "ep_square", "halfmove", "fullmove")

    def __init__(
        self,
        squares: list[str | None],
        turn: str,
        castling: str,
        ep_square: int | None,
        halfmove: int = 0,
        fullmove: int = 1,
    ) -> None:
        self.squares = squares
        self.turn = turn
        self.castling = castling
        self.ep_square = ep_square
        self.halfmove = halfmove
        self.fullmove = fullmove

    # ------------------------------------------------------------------ FEN
    @classmethod
    def from_fen(cls, fen: str) -> Board:
        parts = fen.strip().split()
        if len(parts) < 2:
            raise ValueError(f"invalid FEN (need at least board and turn): {fen!r}")
        placement = parts[0]
        turn = parts[1]
        castling = parts[2] if len(parts) > 2 else "-"
        ep_field = parts[3] if len(parts) > 3 else "-"
        halfmove = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0
        fullmove = int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else 1

        if turn not in (WHITE, BLACK):
            raise ValueError(f"invalid side to move in FEN: {turn!r}")

        squares: list[str | None] = [None] * 64
        ranks = placement.split("/")
        if len(ranks) != 8:
            raise ValueError(f"invalid FEN board (need 8 ranks): {placement!r}")
        for i, row in enumerate(ranks):
            rank = 7 - i  # first FEN rank is rank 8
            file = 0
            for ch in row:
                if ch.isdigit():
                    file += int(ch)
                else:
                    if ch not in "PNBRQKpnbrqk":
                        raise ValueError(f"invalid piece in FEN: {ch!r}")
                    if not _on_board(file, rank):
                        raise ValueError(f"too many squares in FEN rank: {row!r}")
                    squares[square(file, rank)] = ch
                    file += 1
            if file != 8:
                raise ValueError(f"FEN rank does not sum to 8 files: {row!r}")

        ep_square = None if ep_field == "-" else parse_square(ep_field)
        if ep_square is not None:
            # An en-passant target only means something when the opponent has
            # just double-pushed a pawn over it: the target itself is empty, the
            # pawn sits immediately beyond it, and which rank that is follows
            # from whose move it is.  Taken on trust, the field lets ``push``
            # "capture en passant" whatever happens to stand beyond the target -
            # a queen on an untouched square - and the mate search then serves
            # that illegal move as a proven answer.
            ep_rank = 5 if turn == WHITE else 2
            pawn = "p" if turn == WHITE else "P"
            behind = square(file_of(ep_square), 4 if turn == WHITE else 3)
            if (
                rank_of(ep_square) != ep_rank
                or squares[ep_square] is not None
                or squares[behind] != pawn
            ):
                raise ValueError(
                    f"invalid en-passant square in FEN: {ep_field!r} - no pawn has just "
                    f"double-pushed past it, so no en-passant capture is possible"
                )
        # Each side has exactly one king, and the side that just moved cannot
        # have left its own king in check. Without these the mate search runs
        # on positions no game reaches: with the opponent already in check,
        # every move that keeps the check was served as a proven "mate".
        for king in ("K", "k"):
            if squares.count(king) != 1:
                raise ValueError(
                    f"invalid FEN: need exactly one {king!r} king, found {squares.count(king)}"
                )
        board = cls(squares, turn, castling, ep_square, halfmove, fullmove)
        if board.is_check(BLACK if turn == WHITE else WHITE):
            raise ValueError(
                "invalid FEN: the side not to move is in check, which no legal game reaches"
            )
        return board

    def to_fen(self) -> str:
        rows = []
        for rank in range(7, -1, -1):
            row = ""
            empty = 0
            for file in range(8):
                piece = self.squares[square(file, rank)]
                if piece is None:
                    empty += 1
                else:
                    if empty:
                        row += str(empty)
                        empty = 0
                    row += piece
            if empty:
                row += str(empty)
            rows.append(row)
        placement = "/".join(rows)
        castling = self.castling if self.castling else "-"
        ep = "-" if self.ep_square is None else square_name(self.ep_square)
        return f"{placement} {self.turn} {castling} {ep} {self.halfmove} {self.fullmove}"

    # ---------------------------------------------------------------- lookup
    def piece_at(self, sq: int) -> str | None:
        return self.squares[sq]

    def king_square(self, color: str) -> int | None:
        king = "K" if color == WHITE else "k"
        for sq in range(64):
            if self.squares[sq] == king:
                return sq
        return None

    # -------------------------------------------------------------- attacks
    def is_attacked_by(self, sq: int, by_color: str) -> bool:
        """Return True if ``sq`` is attacked by any piece of ``by_color``."""
        f, r = file_of(sq), rank_of(sq)
        pieces = self.squares

        # Pawns.  A pawn of `by_color` attacks `sq` if it sits one rank "behind"
        # (relative to its own advance direction) and one file to the side.
        if by_color == WHITE:
            pawn, pdir = "P", -1  # white pawns come from the rank below
        else:
            pawn, pdir = "p", 1
        for df in (-1, 1):
            pf, pr = f + df, r + pdir
            if _on_board(pf, pr) and pieces[square(pf, pr)] == pawn:
                return True

        # Knights.
        knight = "N" if by_color == WHITE else "n"
        for df, dr in _KNIGHT_DELTAS:
            nf, nr = f + df, r + dr
            if _on_board(nf, nr) and pieces[square(nf, nr)] == knight:
                return True

        # King.
        king = "K" if by_color == WHITE else "k"
        for df, dr in _KING_DELTAS:
            kf, kr = f + df, r + dr
            if _on_board(kf, kr) and pieces[square(kf, kr)] == king:
                return True

        # Sliding pieces: bishops/queens on diagonals, rooks/queens on lines.
        bishop = "B" if by_color == WHITE else "b"
        rook = "R" if by_color == WHITE else "r"
        queen = "Q" if by_color == WHITE else "q"

        for df, dr in _BISHOP_DIRS:
            nf, nr = f + df, r + dr
            while _on_board(nf, nr):
                p = pieces[square(nf, nr)]
                if p is not None:
                    if p in (bishop, queen):
                        return True
                    break
                nf, nr = nf + df, nr + dr

        for df, dr in _ROOK_DIRS:
            nf, nr = f + df, r + dr
            while _on_board(nf, nr):
                p = pieces[square(nf, nr)]
                if p is not None:
                    if p in (rook, queen):
                        return True
                    break
                nf, nr = nf + df, nr + dr

        return False

    def attacks_from(self, sq: int) -> set[int]:
        """Squares the piece on ``sq`` attacks (pseudo-attacks; ignores pins).

        Empty when ``sq`` is empty. Pawns attack only their two forward diagonals.
        A sliding piece's ray stops at (and includes) the first occupied square.
        """
        piece = self.squares[sq]
        if piece is None:
            return set()
        kind = piece.upper()
        f, r = file_of(sq), rank_of(sq)
        out: set[int] = set()
        if kind == "N":
            for df, dr in _KNIGHT_DELTAS:
                if _on_board(f + df, r + dr):
                    out.add(square(f + df, r + dr))
        elif kind == "K":
            for df, dr in _KING_DELTAS:
                if _on_board(f + df, r + dr):
                    out.add(square(f + df, r + dr))
        elif kind == "P":
            pdir = 1 if piece.isupper() else -1
            for df in (-1, 1):
                if _on_board(f + df, r + pdir):
                    out.add(square(f + df, r + pdir))
        else:
            dirs = _BISHOP_DIRS if kind == "B" else _ROOK_DIRS if kind == "R" else _QUEEN_DIRS
            for df, dr in dirs:
                nf, nr = f + df, r + dr
                while _on_board(nf, nr):
                    out.add(square(nf, nr))
                    if self.squares[square(nf, nr)] is not None:
                        break
                    nf, nr = nf + df, nr + dr
        return out

    def is_check(self, color: str | None = None) -> bool:
        color = color or self.turn
        ks = self.king_square(color)
        if ks is None:
            return False
        opponent = BLACK if color == WHITE else WHITE
        return self.is_attacked_by(ks, opponent)

    # ------------------------------------------------------ move generation
    def _pseudo_legal_moves(self) -> Iterable[Move]:
        color = self.turn
        pieces = self.squares
        forward = 1 if color == WHITE else -1
        start_rank = 1 if color == WHITE else 6
        promo_rank = 7 if color == WHITE else 0

        def own(p: str | None) -> bool:
            return p is not None and piece_color(p) == color

        def enemy(p: str | None) -> bool:
            return p is not None and piece_color(p) != color

        for sq in range(64):
            piece = pieces[sq]
            if piece is None or piece_color(piece) != color:
                continue
            f, r = file_of(sq), rank_of(sq)
            kind = piece.upper()

            if kind == "P":
                # Single push.
                one = square(f, r + forward)
                if _on_board(f, r + forward) and pieces[one] is None:
                    if r + forward == promo_rank:
                        for promo in ("q", "r", "b", "n"):
                            yield Move(sq, one, promotion=promo)
                    else:
                        yield Move(sq, one)
                        # Double push.
                        if r == start_rank:
                            two = square(f, r + 2 * forward)
                            if pieces[two] is None:
                                yield Move(sq, two)
                # Captures.
                for df in (-1, 1):
                    cf, cr = f + df, r + forward
                    if not _on_board(cf, cr):
                        continue
                    target = square(cf, cr)
                    if enemy(pieces[target]):
                        if cr == promo_rank:
                            for promo in ("q", "r", "b", "n"):
                                yield Move(sq, target, promotion=promo)
                        else:
                            yield Move(sq, target)
                    elif self.ep_square is not None and target == self.ep_square:
                        yield Move(sq, target, is_ep=True)

            elif kind == "N":
                for df, dr in _KNIGHT_DELTAS:
                    nf, nr = f + df, r + dr
                    if _on_board(nf, nr) and not own(pieces[square(nf, nr)]):
                        yield Move(sq, square(nf, nr))

            elif kind == "K":
                for df, dr in _KING_DELTAS:
                    nf, nr = f + df, r + dr
                    if _on_board(nf, nr) and not own(pieces[square(nf, nr)]):
                        yield Move(sq, square(nf, nr))
                yield from self._castle_moves(color)

            else:  # sliding pieces
                if kind == "B":
                    dirs = _BISHOP_DIRS
                elif kind == "R":
                    dirs = _ROOK_DIRS
                else:  # Q
                    dirs = _QUEEN_DIRS
                for df, dr in dirs:
                    nf, nr = f + df, r + dr
                    while _on_board(nf, nr):
                        target = square(nf, nr)
                        p = pieces[target]
                        if p is None:
                            yield Move(sq, target)
                        else:
                            if enemy(p):
                                yield Move(sq, target)
                            break
                        nf, nr = nf + df, nr + dr

    def _castle_moves(self, color: str) -> Iterable[Move]:
        opponent = BLACK if color == WHITE else WHITE
        pieces = self.squares
        if color == WHITE:
            king_from = square(4, 0)
            if pieces[king_from] != "K":
                return
            # King-side (O-O): f1, g1 empty; e1,f1,g1 not attacked.
            if (
                "K" in self.castling
                and pieces[square(5, 0)] is None
                and pieces[square(6, 0)] is None
                and pieces[square(7, 0)] == "R"
                and not any(self.is_attacked_by(square(x, 0), opponent) for x in (4, 5, 6))
            ):
                yield Move(king_from, square(6, 0), is_castle=True)
            # Queen-side (O-O-O): b1,c1,d1 empty; e1,d1,c1 not attacked.
            if (
                "Q" in self.castling
                and all(pieces[square(x, 0)] is None for x in (1, 2, 3))
                and pieces[square(0, 0)] == "R"
                and not any(self.is_attacked_by(square(x, 0), opponent) for x in (4, 3, 2))
            ):
                yield Move(king_from, square(2, 0), is_castle=True)
        else:
            king_from = square(4, 7)
            if pieces[king_from] != "k":
                return
            if (
                "k" in self.castling
                and pieces[square(5, 7)] is None
                and pieces[square(6, 7)] is None
                and pieces[square(7, 7)] == "r"
                and not any(self.is_attacked_by(square(x, 7), opponent) for x in (4, 5, 6))
            ):
                yield Move(king_from, square(6, 7), is_castle=True)
            if (
                "q" in self.castling
                and all(pieces[square(x, 7)] is None for x in (1, 2, 3))
                and pieces[square(0, 7)] == "r"
                and not any(self.is_attacked_by(square(x, 7), opponent) for x in (4, 3, 2))
            ):
                yield Move(king_from, square(2, 7), is_castle=True)

    def push(self, move: Move) -> Board:
        """Return a new Board with ``move`` applied.  No legality check here."""
        squares = list(self.squares)
        piece = squares[move.from_sq]
        if piece is None:
            raise ValueError(f"no piece on {square_name(move.from_sq)} to move")
        color = piece_color(piece)
        squares[move.from_sq] = None

        # En-passant: remove the captured pawn which sits beside the target.
        if move.is_ep:
            cap_rank = rank_of(move.to_sq) + (-1 if color == WHITE else 1)
            squares[square(file_of(move.to_sq), cap_rank)] = None

        # Place the (possibly promoted) piece.
        if move.promotion:
            squares[move.to_sq] = move.promotion.upper() if color == WHITE else move.promotion
        else:
            squares[move.to_sq] = piece

        # Castling: move the rook too.
        if move.is_castle:
            r = rank_of(move.from_sq)
            if file_of(move.to_sq) == 6:  # king-side
                squares[square(5, r)] = squares[square(7, r)]
                squares[square(7, r)] = None
            else:  # queen-side
                squares[square(3, r)] = squares[square(0, r)]
                squares[square(0, r)] = None

        # Update castling rights.
        new_castling = set(c for c in self.castling if c != "-")

        def drop(*flags: str) -> None:
            for fl in flags:
                new_castling.discard(fl)

        if piece == "K":
            drop("K", "Q")
        elif piece == "k":
            drop("k", "q")
        # Rook moved from its home square.
        if move.from_sq == square(0, 0):
            drop("Q")
        elif move.from_sq == square(7, 0):
            drop("K")
        elif move.from_sq == square(0, 7):
            drop("q")
        elif move.from_sq == square(7, 7):
            drop("k")
        # Rook captured on its home square.
        if move.to_sq == square(0, 0):
            drop("Q")
        elif move.to_sq == square(7, 0):
            drop("K")
        elif move.to_sq == square(0, 7):
            drop("q")
        elif move.to_sq == square(7, 7):
            drop("k")

        castling = "".join(c for c in "KQkq" if c in new_castling) or "-"

        # En-passant target for a double pawn push.
        ep_square = None
        if piece.upper() == "P" and abs(rank_of(move.to_sq) - rank_of(move.from_sq)) == 2:
            ep_square = square(
                file_of(move.from_sq),
                (rank_of(move.from_sq) + rank_of(move.to_sq)) // 2,
            )

        # Half-move clock: reset on pawn move or capture.
        captured = self.squares[move.to_sq] is not None or move.is_ep
        halfmove = 0 if (piece.upper() == "P" or captured) else self.halfmove + 1
        fullmove = self.fullmove + (1 if color == BLACK else 0)
        turn = BLACK if color == WHITE else WHITE

        return Board(squares, turn, castling, ep_square, halfmove, fullmove)

    def legal_moves(self) -> list[Move]:
        color = self.turn
        result: list[Move] = []
        for move in self._pseudo_legal_moves():
            child = self.push(move)
            ks = child.king_square(color)
            if ks is None:
                continue
            opponent = BLACK if color == WHITE else WHITE
            if not child.is_attacked_by(ks, opponent):
                result.append(move)
        return result

    def is_checkmate(self) -> bool:
        return self.is_check(self.turn) and not self.legal_moves()

    def is_stalemate(self) -> bool:
        return not self.is_check(self.turn) and not self.legal_moves()

    # --------------------------------------------------------------- render
    def ascii(self, perspective: str = WHITE) -> str:
        """Return an ASCII rendering of the board.

        ``.`` marks an empty square; uppercase = white, lowercase = black.
        """
        ranks = range(7, -1, -1) if perspective == WHITE else range(0, 8)
        files = range(0, 8) if perspective == WHITE else range(7, -1, -1)
        lines = ["  +------------------------+"]
        for r in ranks:
            cells = []
            for f in files:
                p = self.squares[square(f, r)]
                cells.append(p if p is not None else ".")
            lines.append(f"{r + 1} | " + " ".join(cells) + " |")
        lines.append("  +------------------------+")
        file_labels = "a b c d e f g h" if perspective == WHITE else "h g f e d c b a"
        lines.append("    " + file_labels)
        return "\n".join(lines)


# ---------------------------------------------------------------- utilities
def move_from_uci(board: Board, uci: str) -> Move:
    """Build a fully-specified :class:`Move` for a UCI string in ``board``.

    This resolves en-passant and castling flags from the position so that the
    resulting move behaves correctly when pushed.  Raises ``ValueError`` if the
    move is not legal in ``board``.
    """
    uci = uci.strip()
    if len(uci) not in (4, 5):
        raise ValueError(f"invalid UCI move: {uci!r}")
    from_sq = parse_square(uci[0:2])
    to_sq = parse_square(uci[2:4])
    promotion = uci[4].lower() if len(uci) == 5 else None
    for move in board.legal_moves():
        if move.from_sq == from_sq and move.to_sq == to_sq and move.promotion == promotion:
            return move
    raise ValueError(f"illegal move {uci!r} in position {board.to_fen()!r}")


def move_to_san(board: Board, move: Move) -> str:
    """Return the Standard Algebraic Notation (SAN) for ``move`` in ``board``.

    ``move`` must be legal in ``board``.  The result mirrors the conventions of
    mature engines (e.g. ``Ra8#``, ``exd6``, ``a8=Q+``, ``O-O-O``): a piece
    letter (omitted for pawns), the minimal file/rank disambiguation when more
    than one identical piece can reach the target, an ``x`` for captures, the
    destination square, a promotion suffix, and a trailing ``+`` for check or
    ``#`` for checkmate.
    """
    piece = board.piece_at(move.from_sq)
    if piece is None:
        raise ValueError(f"no piece on {square_name(move.from_sq)} to move")
    kind = piece.upper()

    if move.is_castle:
        san = "O-O" if file_of(move.to_sq) == 6 else "O-O-O"
    else:
        is_capture = board.piece_at(move.to_sq) is not None or move.is_ep
        if kind == "P":
            san = ""
            if is_capture:
                san += "abcdefgh"[file_of(move.from_sq)] + "x"
            san += square_name(move.to_sq)
            if move.promotion:
                san += "=" + move.promotion.upper()
        else:
            san = kind + _san_disambiguation(board, move, piece)
            if is_capture:
                san += "x"
            san += square_name(move.to_sq)

    child = board.push(move)
    if child.is_checkmate():
        san += "#"
    elif child.is_check():
        san += "+"
    return san


def _san_disambiguation(board: Board, move: Move, piece: str) -> str:
    """Return the minimal file/rank hint needed to disambiguate ``move``.

    Considers only *legal* moves of the same piece type/colour that also land on
    ``move.to_sq`` from a different origin, matching standard SAN rules.
    """
    others = [
        m.from_sq
        for m in board.legal_moves()
        if m.to_sq == move.to_sq
        and m.from_sq != move.from_sq
        and board.piece_at(m.from_sq) == piece
    ]
    if not others:
        return ""
    same_file = any(file_of(sq) == file_of(move.from_sq) for sq in others)
    same_rank = any(rank_of(sq) == rank_of(move.from_sq) for sq in others)
    if not same_file:
        return "abcdefgh"[file_of(move.from_sq)]
    if not same_rank:
        return str(rank_of(move.from_sq) + 1)
    return square_name(move.from_sq)


def parse_san(board: Board, san: str) -> Move:
    """Parse Standard Algebraic Notation into a legal :class:`Move` for ``board``.

    Handles piece letters, file/rank disambiguation, captures, pawn promotions
    (``e8=Q``), castling (``O-O`` / ``O-O-O``, also ``0-0``), en passant, and any
    trailing ``+`` / ``#`` suffix. Resolves against the actual legal moves and
    raises ``ValueError`` unless the SAN names exactly one legal move (an
    illegal, ambiguous or malformed SAN fails loud).
    """
    if not isinstance(san, str):
        raise TypeError(f"san must be a string, got {san!r}")
    text = san.strip().rstrip("+#")
    if not text:
        raise ValueError("empty SAN")

    legal = list(board.legal_moves())

    normalized = text.replace("0", "O")
    if normalized in ("O-O", "O-O-O"):
        kingside = normalized == "O-O"
        matches = [m for m in legal if m.is_castle and (file_of(m.to_sq) == 6) == kingside]
        if len(matches) == 1:
            return matches[0]
        side = "king" if kingside else "queen"
        raise ValueError(f"no legal {side}-side castling for SAN {san!r}")

    promotion: str | None = None
    body = text
    if len(body) >= 2 and body[-2] == "=":
        promo = body[-1].upper()
        if promo not in "QRBN":
            raise ValueError(f"invalid promotion piece in SAN {san!r}")
        promotion = promo
        body = body[:-2]

    if body and body[0] in "NBRQK":
        kind = body[0]
        rest = body[1:]
    else:
        kind = "P"
        rest = body

    rest = rest.replace("x", "")
    if len(rest) < 2:
        raise ValueError(f"malformed SAN {san!r} (no destination square)")
    try:
        dest = parse_square(rest[-2:])
    except ValueError as exc:
        raise ValueError(f"malformed SAN {san!r}: {exc}") from None

    disamb_file: int | None = None
    disamb_rank: int | None = None
    for ch in rest[:-2]:
        if ch in "abcdefgh":
            disamb_file = "abcdefgh".index(ch)
        elif ch in "12345678":
            disamb_rank = int(ch) - 1
        else:
            raise ValueError(f"malformed SAN disambiguation in {san!r}")

    want = kind if board.turn == WHITE else kind.lower()
    candidates: list[Move] = []
    for m in legal:
        if m.to_sq != dest or board.piece_at(m.from_sq) != want:
            continue
        mp = m.promotion.upper() if m.promotion else None
        if mp != promotion:
            continue
        if disamb_file is not None and file_of(m.from_sq) != disamb_file:
            continue
        if disamb_rank is not None and rank_of(m.from_sq) != disamb_rank:
            continue
        candidates.append(m)

    if len(candidates) == 1:
        return candidates[0]
    if not candidates:
        raise ValueError(f"no legal move matches SAN {san!r}")
    raise ValueError(f"ambiguous SAN {san!r}: {len(candidates)} legal moves match")


def game_ending_refutation(board: Board) -> str | None:
    """Why a material "win" that led to ``board`` is no win, or None.

    ``board`` is the position right after the winning side's move, with the
    defender to move. A material count cannot see that the move stalemated the
    defender (a draw) or left a mate in one against the mover; both are checked
    here so the verifier and the fork prover reject them the same way.
    """
    replies = board.legal_moves()
    if not replies:
        return None if board.is_check() else "stalemates the opponent (a draw)"
    for reply in replies:
        if board.push(reply).is_checkmate():
            return f"allows mate in one ({reply.uci()})"
    return None


def perft(board: Board, depth: int) -> int:
    """Count leaf nodes of the legal move tree to ``depth`` (a move-gen pin).

    ``perft(board, 0)`` is 1; otherwise it is the sum over every legal move of
    ``perft(child, depth - 1)``. Matching known reference perft counts is a
    strong, position-independent check that legal move generation is correct.
    """
    if depth < 0:
        raise ValueError(f"perft depth must be >= 0, got {depth}")
    if depth == 0:
        return 1
    return sum(perft(board.push(move), depth - 1) for move in board.legal_moves())


def forced_mate_move(board: Board, depth: int) -> str | None:
    """Return a UCI move that forces mate in at most ``depth`` moves, else None.

    ``depth`` counts *moves by the side to move* (a "mate in N").  The search is
    a small exhaustive minimax over legal moves and is intended for the tiny
    depths (1 and 2) used by this project's puzzles.
    """
    if depth < 1:
        return None
    for move in board.legal_moves():
        child = board.push(move)
        if child.is_checkmate():
            return move.uci()
        if depth > 1 and _forces_mate_after_reply(child, depth - 1):
            return move.uci()
    return None


def _forces_mate_after_reply(board: Board, depth: int) -> bool:
    """True if the side *just moved* mates within ``depth`` for every reply.

    ``board`` is the position with the *defender* to move.  The defender must
    have at least one legal move (otherwise it is already mate or stalemate),
    and every such reply must allow the attacker to force mate in ``depth``.
    """
    replies = board.legal_moves()
    if not replies:
        return False  # already mate/stalemate, handled by the caller
    for reply in replies:
        after = board.push(reply)
        if forced_mate_move(after, depth) is None:
            return False
    return True
