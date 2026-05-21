"""
conftest.py — adds phase-1/src and project root to sys.path
so tests can import collector modules and shared modules directly.
"""
import sys
import os

# Project root (contains shared/)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
# phase-1/src (contains collector modules)
SRC = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))

for path in (ROOT, SRC):
    if path not in sys.path:
        sys.path.insert(0, path)
