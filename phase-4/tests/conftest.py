"""
conftest.py — path setup for Phase 4 tests.
"""
import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))

for path in (ROOT, SRC):
    if path not in sys.path:
        sys.path.insert(0, path)
