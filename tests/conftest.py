"""
Shared pytest setup.

`backend/main.py` imports its own siblings with bare paths (`from parsers.aws_parser
import ...`), which only resolves when `backend/` itself is on sys.path -- the same
assumption `backend/pyrightconfig.json`'s `extraPaths: ["."]` encodes. These tests
import the same way the server does, so they exercise the real import graph
(including `services/csv_ingest.py`, which can't be imported any other way).
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
