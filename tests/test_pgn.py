"""Mainline PGN reader: headers, movetext, comments, NAGs, variations, results.

The reader is notation-only (SAN legality is proven later by the miner through
parse_san), so these tests pin two things: (a) well-formed PGN yields exactly
the mainline SAN tokens, and (b) malformed PGN fails LOUD with an error naming
the game and line - never a silent misparse.
"""

import pytest

from palamedes.pgn import PgnError, read_games

SIMPLE = """\
[Event "Test"]
[Result "1-0"]

1. e4 e5 2. Nf3 Nc6 3. Bb5 a6 1-0
"""

TWO_GAMES = """\
[Event "First"]
[Result "1-0"]

1. e4 e5 1-0

[Event "Second"]
[Result "0-1"]

1. d4 d5 2. c4 0-1
"""

ANNOTATED = """\
[Event "Annotated"]
[Result "1/2-1/2"]

1. e4 {best by test} e5 $1 2. Nf3 (2. f4 {the gambit} exf4 (3... d5)) 2... Nc6
3. Bb5 ; a rest-of-line comment
3... a6 1/2-1/2
"""


def test_reads_tags_moves_and_result():
    games = read_games(SIMPLE)
    assert len(games) == 1
    game = games[0]
    assert game.tags["Event"] == "Test"
    assert game.tags["Result"] == "1-0"
    assert game.moves == ("e4", "e5", "Nf3", "Nc6", "Bb5", "a6")
    assert game.result == "1-0"
    assert game.game_number == 1


def test_reads_multiple_games_per_file():
    games = read_games(TWO_GAMES)
    assert [g.tags["Event"] for g in games] == ["First", "Second"]
    assert games[0].moves == ("e4", "e5")
    assert games[1].moves == ("d4", "d5", "c4")
    assert games[1].result == "0-1"
    assert games[1].game_number == 2


def test_strips_comments_nags_and_recursive_variations():
    (game,) = read_games(ANNOTATED)
    # Only the mainline survives: brace comments, $-NAGs, semicolon comments
    # and (nested) parenthesised variations are all stripped.
    assert game.moves == ("e4", "e5", "Nf3", "Nc6", "Bb5", "a6")
    assert game.result == "1/2-1/2"


def test_castling_promotion_and_suffixed_tokens_are_kept_verbatim():
    text = '[Result "1-0"]\n\n1. O-O! e8=Q?? 2. Rf8# 1-0\n'
    (game,) = read_games(text)
    # '!'/'?' annotations are dropped from the token; '+'/'#' stay (parse_san
    # tolerates them), as do '=Q' promotions and castling.
    assert game.moves == ("O-O", "e8=Q", "Rf8#")


def test_movetext_without_tag_section_is_accepted():
    (game,) = read_games("1. e4 e5 *\n")
    assert game.moves == ("e4", "e5")
    assert game.result == "*"
    assert game.tags == {}


def test_empty_or_blank_input_yields_no_games():
    assert read_games("") == []
    assert read_games("\n  \n") == []


# ------------------------------------------------------------ loud failures
def test_malformed_tag_line_fails_loud():
    with pytest.raises(PgnError, match=r"game 1.*line 1"):
        read_games('[Event no quotes]\n\n1. e4 *\n')


def test_unterminated_brace_comment_fails_loud():
    with pytest.raises(PgnError, match=r"game 1.*line 3.*comment"):
        read_games('[Result "*"]\n\n1. e4 {never closed *\n')


def test_unterminated_variation_fails_loud():
    with pytest.raises(PgnError, match=r"game 1.*line 3.*variation"):
        read_games('[Result "*"]\n\n1. e4 (1. d4 d5 *\n')


def test_unmatched_closing_paren_fails_loud():
    with pytest.raises(PgnError, match=r"game 1.*line 3"):
        read_games('[Result "*"]\n\n1. e4 ) e5 *\n')


def test_missing_result_at_end_of_input_fails_loud():
    with pytest.raises(PgnError, match=r"game 1.*result"):
        read_games('[Event "Truncated"]\n\n1. e4 e5 2. Nf3\n')


def test_garbage_token_fails_loud_and_names_the_line():
    with pytest.raises(PgnError, match=r"game 1.*line 4"):
        read_games('[Event "Bad"]\n[Result "*"]\n\n1. e4 e9x!zz *\n')


def test_error_in_second_game_names_game_2():
    text = '[Result "1-0"]\n\n1. e4 e5 1-0\n\n[Result "*"]\n\n1. d4 {oops *\n'
    with pytest.raises(PgnError, match=r"game 2"):
        read_games(text)


def test_bare_nag_without_digits_fails_loud():
    with pytest.raises(PgnError, match=r"game 1"):
        read_games('[Result "*"]\n\n1. e4 $ e5 *\n')
