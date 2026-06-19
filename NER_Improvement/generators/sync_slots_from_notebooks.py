"""
Refresh slot JSON files from InshallahDataset notebooks.
Delegates to CLF_Improvement/generators/sync_slots_from_notebooks.py
"""

from __future__ import annotations

import runpy
from pathlib import Path

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "CLF_Improvement"
    / "generators"
    / "sync_slots_from_notebooks.py"
)

if __name__ == "__main__":
    runpy.run_path(str(SCRIPT), run_name="__main__")
