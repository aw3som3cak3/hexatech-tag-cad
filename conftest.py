"""Root conftest: put src/ on sys.path so tests import hexa.* without install."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
