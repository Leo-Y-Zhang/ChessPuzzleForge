"""Ensure the project root is importable when running ``pytest`` directly.

Running ``python -m pytest`` already puts the current directory on ``sys.path``,
but this makes a bare ``pytest`` invocation work too.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
