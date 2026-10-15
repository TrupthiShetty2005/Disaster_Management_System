#!/usr/bin/env python
"""Populate the complete VisionGuard demo incident (same as app.db.seed)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))

from app.db.init_db import init_db
from app.db.seed import seed_if_empty


def main() -> None:
    init_db()
    seed_if_empty()
    print("Demo incident seeded (Kuttanad flood).")


if __name__ == "__main__":
    main()
