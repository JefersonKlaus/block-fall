"""Test package for Block Fall.

The app lives in src/ (the usual layout); make it importable for the tests.
"""

import sys
from pathlib import Path

SRC = str(Path(__file__).resolve().parent.parent / "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)
