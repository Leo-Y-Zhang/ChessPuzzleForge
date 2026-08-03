# Design Brief — terminal output

**Date:** 2026-08-03 · **PRD:** [PRD.md](PRD.md) · **App Flow:** [APP_FLOW.md](APP_FLOW.md)

> The only rendered surface in this project is text on a terminal:
> `Board.ascii()` (the diagram) and `generator.render_puzzle()` (the block
> around it), plus two machine formats, `puzzle_to_json` and `puzzle_to_pgn`.
> That is a small surface, so this is a short brief. Every measurement below was
> taken from the actual output.

## Intent

It should read like **a diagram in a chess book**: static, plain, and finished
the moment it is printed. The tool's whole claim is that its answers are
proven, so the presentation should get out of the way and let the position
speak — no ornament that implies effort or cleverness the program has not done.

It must never feel like a dashboard. No spinners, no progress bars, no
redrawn lines, no colour-coded severity, nothing that suggests a long-running
service. A run is a single short computation that prints a result and exits,
and the output should look exactly like that.

## Who is looking at it

Someone at a terminal, mid-session, who has just typed a command and wants the
position **now** — usually with the terminal only one of several windows and
often at a small size. Frequently the same person five minutes later, reading
`mined.jsonl` through `jq` rather than looking at boards at all. Occasionally
CI, which reads the same bytes and must get identical ones.

Design for the person who will pipe this. Every reader of this output is
either scanning it in two seconds or feeding it to another program.

## Precedents

- **`git status` / `git diff` stream discipline.** Human commentary and
  machine-consumable content are never mixed in one stream. This project takes
  the same rule literally: puzzle data to stdout, progress and errors to
  stderr, so `--mine games.pgn > mined.jsonl` gives a clean file while the
  human still sees `game 1/1: replayed 33 plies, 3 new puzzles`.
- **A printed chess diagram.** Fixed grid, rank digits down the left, file
  letters along the bottom, one glyph per square, orientation from the side to
  move. `render_puzzle` passes `perspective=board.turn`, so a black-to-move
  puzzle is shown from Black's side — the reader never has to mentally rotate.
- **FEN itself.** The most useful thing on screen is the line that lets you
  leave: every rendered puzzle prints its FEN, so the position can be pasted
  into any other tool. That is designed-in humility, and it stays.

## Anti-patterns for this project

Specific enough to enforce in review:

- **Unicode chess pieces (`♞`).** Ambiguous-width in many terminals, so the
  grid shifts; unavailable in several code pages; announced inconsistently by
  screen readers. ASCII `PNBRQK` / `pnbrqk` is unambiguous and already encodes
  colour by case.
- **Box-drawing characters** for the frame. Same failure mode on a Windows
  console that is not in UTF-8. `+`, `-`, `|` render everywhere.
- **Colour.** It would be the *only* signal for whatever it marked, it breaks
  in pipes, and it makes CI transcripts noisy. Status is carried by words.
- **Anything on stdout that is not puzzle data.** A progress line in the JSON
  stream is a correctness bug, not a cosmetic one.
- **Cursor control, `\r` rewriting, spinners.** They destroy the output in a
  log, a pipe, a CI run and a braille display simultaneously.
- **Emoji or decorative rules.** They read as AI-generated polish and add
  nothing a chess player wants.

## The grid

Monospace is assumed — it is a terminal. The board is a fixed 8×8 of
single-character cells separated by one space, `.` for empty, uppercase White,
lowercase Black. That gives a cell pitch of 2 columns and a board body 15
columns wide, inset 4 columns from the left so the rank digit and the frame sit
in front of it. The file-label row is inset to match, so labels sit under their
files.

Nothing wraps: the widest line in a rendered puzzle is the FEN, comfortably
under 80 columns for any legal position.

### Defect: the frame is 7 columns too wide

Measured, not inferred:

```
28  '  +------------------------+'
21  '8 | . . . . . . k . |'
19  '    a b c d e f g h'
```

The rank rows put their closing `|` at column 20; the border's closing `+` is
at column 27. The border carries 24 dashes where the content between the bars
is 17 characters, so **the frame should be 17 dashes, not 24** — the rest of
the layout is already correct and needs no change.

It is cosmetic: it affects neither the FEN, the JSON, the PGN, nor any test.
But it is visible in the README's own example output, and a design brief that
quietly omitted it would be worth nothing. **Not fixed here** — the change that
prompted this document was documentation and naming only, and a rendering
change belongs in its own commit with a golden-output test.

## Signal vocabulary

There is no colour, so meaning is carried entirely by words, position and
stream. The full vocabulary:

| Signal | Where | Means |
|---|---|---|
| `PASS` / `FAIL` | stdout, `--verify-all` | per-puzzle verification result |
| `Correct!` / `Not the solution:` | stdout, `--solve` | judgement of the user's move |
| `Mining failed:` / `Synthesis failed:` / `Invalid FEN:` / `Cannot read PGN file:` | **stderr** | the run did not produce an answer |
| `(Run again with --reveal to see the solution.)` | stdout | the solution exists and is being withheld |
| `game 1/1: replayed 33 plies, 3 new puzzles (3 total)` | **stderr** | progress, never mixed into the data |

Every failure message names the offending thing — the game and move, the
unsupported piece letter, the goal *and* the difficulty that matched nothing —
and, where a remedy exists, names it.

## States

- **Withheld** (default): board and FEN, no solution, plus the one line saying
  how to see it.
- **Revealed** (`--reveal`): adds `Solution: Qd8#  (UCI: d1d8)` — SAN for the
  human, UCI in parentheses for the machine, always both.
- **Prompt** (`--solve`): board, a blank line, the instruction naming both
  accepted notations, then `> `. The prompt is the last thing on screen.
- **Judged**: one line, then exit. No follow-up question, no retry loop.
- **Batch** (`--mine`, `--synth --count`): no board at all. One JSON object per
  line, keys sorted, so the output diffs cleanly and sorts stably.
- **Error**: one line on stderr, nonzero exit, no partial puzzle.

## Terminal width

The output does not adapt and deliberately does not try. It assumes ≥ 80
columns, never queries the terminal size, and never reflows — because reflowing
would make the output depend on the environment, and identical input must
produce identical bytes for the golden-digest test to mean anything. A narrow
terminal wraps; that is the terminal's decision, not the program's.

## Accessibility floor — non-negotiable

The web floor in the template (contrast ratios, touch targets, 200% zoom) does
not apply to a program that emits plain text. The terminal equivalents do, and
they are met:

- ASCII only — legible under any code page, correct through a screen reader.
- Colour is never a signal, because there is no colour.
- No cursor control or rewritten lines: everything printed stays printed and
  can be scrolled back, piped, logged or read by a braille display.
- Keyboard-only by construction; Ctrl-C and EOF both exit with a message, not
  a traceback.
- A machine-readable escape hatch always exists — the FEN on every rendered
  puzzle, and JSON in every batch mode — so nobody is forced to parse the
  ASCII diagram.

## Done means

- [x] Reads like a book diagram: static, plain, finished when printed.
- [x] Data on stdout, everything else on stderr, verified by the CLI tests.
- [x] ASCII only; no colour; no cursor control.
- [x] Every error names the offending input and, where one exists, a remedy.
- [x] Byte-identical output for identical input, pinned by the golden digest.
- [ ] **Board frame aligned** — currently 24 dashes where 17 are needed.
      Deferred to its own commit with a golden-output test.
