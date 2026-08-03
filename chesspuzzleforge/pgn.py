"""A mainline PGN reader - pure standard library, fail-loud.

Reads Portable Game Notation well enough to replay games: tag-pair headers
(``[Event "..."]``), movetext with move numbers (spaced ``1. e4`` or glued
ChessBase-style ``1.e4`` / ``2...Nc6``), brace comments ``{...}``, semicolon
rest-of-line comments, numeric annotation glyphs (``$12``), game results
(``1-0`` / ``0-1`` / ``1/2-1/2`` / ``*``), and multiple games per file.

**Mainline only**: parenthesised recursive annotation variations are skipped
(including nested ones, and comments inside them); their contents are not
validated. Trailing ``!`` / ``?`` annotations are dropped from move tokens;
``+`` / ``#`` suffixes are kept (``parse_san`` tolerates them).

Fail-loud contract: malformed input raises :class:`PgnError` (a ``ValueError``)
naming the game and line - the reader never silently misparses. This module
reads *notation* only; SAN tokens are validated for shape here, and their
legality is proven later when the miner replays them through ``parse_san``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

RESULTS = ("1-0", "0-1", "1/2-1/2", "*")

# Shape (not legality) of a single SAN token, after '!'/'?' suffixes are dropped.
_SAN_SHAPE = re.compile(
    r"(O-O(-O)?[+#]?|0-0(-0)?[+#]?|[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](=[QRBN])?[+#]?)$"
)
# A move-number token: digits with any number of trailing periods (1. / 2... / 3).
# A real move number never starts with 0, so a nonstandard all-digit token like
# a "00" castling attempt fails loud instead of silently desyncing the replay.
_MOVE_NUMBER = re.compile(r"[1-9]\d*\.*$")
# A move number glued to its SAN with no space (ChessBase-style 1.e4 / 2...Nc6).
_GLUED_MOVE_NUMBER = re.compile(r"[1-9]\d*\.+")
_TAG_PAIR = re.compile(r'\[\s*(\w+)\s+"((?:[^"\\]|\\.)*)"\s*\]')


class PgnError(ValueError):
    """Malformed PGN input; the message names the offending game and line."""


@dataclass(frozen=True)
class PgnGame:
    """One game record: its tag pairs and the mainline SAN tokens, in order."""

    game_number: int
    tags: dict[str, str] = field(compare=False)
    moves: tuple[str, ...] = ()
    result: str = "*"


class _Scanner:
    """Character scanner over the PGN text, tracking the current line number."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0
        self.line = 1

    def eof(self) -> bool:
        return self.pos >= len(self.text)

    def peek(self) -> str:
        return self.text[self.pos]

    def advance(self) -> str:
        ch = self.text[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
        return ch

    def skip_whitespace(self) -> None:
        while not self.eof() and self.peek().isspace():
            self.advance()

    def skip_to_end_of_line(self) -> None:
        while not self.eof() and self.peek() != "\n":
            self.advance()

    def read_token(self) -> str:
        """Read up to the next whitespace or structural character."""
        start = self.pos
        while not self.eof() and not self.peek().isspace() and self.peek() not in "(){};[":
            self.advance()
        return self.text[start:self.pos]


def _error(game_number: int, line: int, detail: str) -> PgnError:
    return PgnError(f"malformed PGN in game {game_number} (line {line}): {detail}")


def _read_tag_pairs(scanner: _Scanner, game_number: int) -> dict[str, str]:
    tags: dict[str, str] = {}
    while True:
        scanner.skip_whitespace()
        if scanner.eof() or scanner.peek() != "[":
            return tags
        line = scanner.line
        match = _TAG_PAIR.match(scanner.text, scanner.pos)
        if match is None:
            raise _error(game_number, line, "malformed tag pair (expected [Name \"value\"])")
        while scanner.pos < match.end():
            scanner.advance()
        tags[match.group(1)] = match.group(2).replace('\\"', '"').replace("\\\\", "\\")


def _skip_brace_comment(scanner: _Scanner, game_number: int) -> None:
    line = scanner.line
    scanner.advance()  # consume '{'
    while not scanner.eof():
        if scanner.advance() == "}":
            return
    raise _error(game_number, line, "unterminated { comment")


def _skip_variation(scanner: _Scanner, game_number: int) -> None:
    """Skip a parenthesised variation, including nested ones and comments inside."""
    line = scanner.line
    scanner.advance()  # consume '('
    depth = 1
    while not scanner.eof():
        ch = scanner.peek()
        if ch == "{":
            _skip_brace_comment(scanner, game_number)
        elif ch == "(":
            scanner.advance()
            depth += 1
        elif ch == ")":
            scanner.advance()
            depth -= 1
            if depth == 0:
                return
        else:
            scanner.advance()
    raise _error(game_number, line, "unterminated ( variation")


def _read_movetext(scanner: _Scanner, game_number: int) -> tuple[tuple[str, ...], str]:
    """Read mainline SAN tokens until the game's result token."""
    moves: list[str] = []
    while True:
        scanner.skip_whitespace()
        if scanner.eof():
            raise _error(game_number, scanner.line, "movetext ended without a game result")
        ch = scanner.peek()
        line = scanner.line
        if ch == "{":
            _skip_brace_comment(scanner, game_number)
        elif ch == "(":
            _skip_variation(scanner, game_number)
        elif ch == ")":
            raise _error(game_number, line, "unmatched ) outside any variation")
        elif ch == ";":
            scanner.skip_to_end_of_line()
        elif ch == "[":
            raise _error(game_number, line, "new tag section before a game result")
        else:
            token = scanner.read_token()
            if not token:  # pragma: no cover - structural chars are handled above
                raise _error(game_number, line, f"unexpected character {ch!r}")
            if token in RESULTS:
                return tuple(moves), token
            if token == "$":
                raise _error(game_number, line, "numeric annotation glyph $ without digits")
            if token.startswith("$"):
                if not token[1:].isdigit():
                    raise _error(game_number, line, f"malformed annotation glyph {token!r}")
                continue
            if _MOVE_NUMBER.match(token) or set(token) == {"."}:
                continue  # move-number decoration (1. / 2... / a bare ...)
            san = token
            glued = _GLUED_MOVE_NUMBER.match(san)
            if glued is not None:
                san = san[glued.end():]  # 1.e4 -> e4, 2...Nc6 -> Nc6
            san = san.rstrip("!?")
            if not san or not _SAN_SHAPE.match(san):
                raise _error(game_number, line, f"unrecognised movetext token {token!r}")
            moves.append(san)


def read_games(text: str) -> list[PgnGame]:
    """Parse every game in ``text``; raise :class:`PgnError` on malformed input."""
    scanner = _Scanner(text)
    games: list[PgnGame] = []
    while True:
        scanner.skip_whitespace()
        if scanner.eof():
            return games
        game_number = len(games) + 1
        line = scanner.line
        tags = _read_tag_pairs(scanner, game_number)
        moves, result = _read_movetext(scanner, game_number)
        if not tags and not moves:
            # A stray trailing result token would otherwise become a phantom
            # empty game (e.g. '1. e4 * 1-0' parsing as two games).
            raise _error(game_number, line, f"stray result {result!r} with no tags and no moves")
        games.append(PgnGame(game_number=game_number, tags=tags, moves=moves, result=result))
