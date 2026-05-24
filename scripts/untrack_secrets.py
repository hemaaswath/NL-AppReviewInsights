"""Remove accidentally tracked secret files from git index (keeps local copies)."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CANDIDATES = [
    ".env",
    ".streamlit/secrets.toml",
    ".streamlit/secrets_export.txt",
    "MCPServer/saksham-mcp-server/token.json",
    "MCPServer/saksham-mcp-server/credentials.json",
]


def main() -> int:
    removed = []
    for rel in CANDIDATES:
        check = subprocess.run(
            ["git", "ls-files", "--error-unmatch", rel],
            cwd=ROOT,
            capture_output=True,
        )
        if check.returncode == 0:
            subprocess.run(["git", "rm", "--cached", "-f", rel], cwd=ROOT, check=True)
            removed.append(rel)

    # Any tracked path ending with secret basenames
    ls = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    for line in ls.stdout.splitlines():
        p = line.strip().replace("\\", "/")
        if not p or p.endswith(".example"):
            continue
        base = Path(p).name
        if base in {"token.json", "credentials.json", "secrets.toml"} or p == ".env":
            subprocess.run(["git", "rm", "--cached", "-f", p], cwd=ROOT, check=False)
            if p not in removed:
                removed.append(p)

    if removed:
        print("Untracked from git (files kept on disk):")
        for p in removed:
            print(f"  {p}")
        print("\nCommit this change, then rotate any keys that were ever pushed.")
    else:
        print("No secret files were tracked by git.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
