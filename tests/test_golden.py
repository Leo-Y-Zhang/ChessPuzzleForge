"""Determinism tripwire: a pinned digest of the whole bank's deterministic JSON.

If this digest changes, the bank or the JSON export changed - regenerate
GOLDEN_DIGEST only on an intentional change, and say why in the commit message.
"""

import hashlib

from chesspuzzleforge.export import puzzle_to_json
from chesspuzzleforge.fen_bank import all_puzzles

GOLDEN_DIGEST = "0a4ca774cc89612915ea19ec41a2eeb2804777dbdb15b844b3987eaa21e5e6cf"


def _bank_digest() -> str:
    puzzles = sorted(all_puzzles(), key=lambda p: p["id"])
    blob = "\n".join(puzzle_to_json(p) for p in puzzles)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def test_bank_export_digest_is_stable():
    assert _bank_digest() == GOLDEN_DIGEST


def test_bank_export_is_deterministic_on_repeat():
    assert _bank_digest() == _bank_digest()
