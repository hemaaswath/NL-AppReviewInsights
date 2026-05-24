"""
Ensure secret files are never tracked by git and not sitting as staged changes.
Run from pre-push, CI, or manually: python scripts/guard_repo_secrets.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SECRET_BASENAMES = {
    ".env",
    "secrets.toml",
    "secrets_export.txt",
    "token.json",
    "credentials.json",
    "oauth_authorize_url.txt",
    ".oauth_client_id",
}


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def tracked_secret_paths() -> list[str]:
    out = _git("ls-files")
    if out.returncode != 0:
        return []
    bad = []
    for line in out.stdout.splitlines():
        p = line.strip().replace("\\", "/")
        if not p:
            continue
        name = Path(p).name
        if name in SECRET_BASENAMES and not p.endswith(".example"):
            bad.append(p)
        if "secrets_export" in p.lower():
            bad.append(p)
    return bad


def staged_secret_paths() -> list[str]:
    out = _git("diff", "--cached", "--name-only")
    return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]


def main() -> int:
    from secret_scan import path_is_blocked, scan_paths

    tracked = tracked_secret_paths()
    if tracked:
        print("FATAL: Secret files are TRACKED by git (will push to GitHub):")
        for p in tracked:
            print(f"  {p}")
        print("\nFix (run from repo root):")
        print("  python scripts/untrack_secrets.py")
        print("  git commit -m \"Stop tracking secret files\"")
        return 1

    staged = staged_secret_paths()
    blocked, content_bad = scan_paths(staged, ROOT)
    if blocked or content_bad:
        print("FATAL: Staged files contain secrets.")
        for p in blocked:
            print(f"  blocked path: {p}")
        for p in content_bad:
            print(f"  {p}")
        return 1

    print("OK: no secret files tracked; staging area clean.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
