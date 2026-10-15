#!/usr/bin/env python
"""Seed the backend database (wrapper around app.db.seed)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
os.chdir(BACKEND)
sys.path.insert(0, str(BACKEND))

from app.db.init_db import init_db
from app.db.seed import seed_if_empty

init_db()
seed_if_empty()
print("Database seeded.")
