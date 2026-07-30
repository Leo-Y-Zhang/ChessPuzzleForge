"""The package __version__ and pyproject version stay in lockstep at the current release."""

import re
from pathlib import Path

import palamedes

PYPROJECT = Path(__file__).resolve().parents[1] / "pyproject.toml"


def test_version_is_the_current_release():
    assert palamedes.__version__ == "2.1.0"


def test_pyproject_version_matches_package():
    text = PYPROJECT.read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    assert match is not None and match.group(1) == palamedes.__version__
