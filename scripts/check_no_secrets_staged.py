"""Cross-platform check: fail if secret files are staged for commit."""
from __future__ import annotations

import re
import subprocess
import sys

BLOCKED = re.compile(
    r"(\.env$|\.env\.|secrets\.toml$|secrets_export|token\.json$|credentials\.json$|oauth_authorize_url)",
    re.I,
)

def main() -> int:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=False,
    )
    staged = [line.strip() for line in out.stdout.splitlines() if line.strip()]
    if not staged:
        print("OK: no staged files.")
        return 0

    bad = [f for f in staged if BLOCKED.search(f.replace("\\", "/"))]
    if bad:
        print("REFUSING COMMIT — secret files staged:\n  " + "\n  ".join(bad))
        print("\nUnstage: git reset HEAD -- <file>")
        print("Secrets belong in .env (local) and Streamlit Cloud UI — NOT in GitHub.")
        return 1
    print("OK: no secret files staged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
