"""Cross-platform check: fail if secret files or secret content are staged."""
from __future__ import annotations

import sys
from pathlib import Path

# Delegate to full scanner (paths + content)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from secret_scan import main as scan_main  # noqa: E402


if __name__ == "__main__":
    sys.argv = [sys.argv[0], "staged"]
    sys.exit(scan_main())
