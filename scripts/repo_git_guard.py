"""Git safety: block secret files from ever being committed or pushed."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def repo_has_tracked_secrets() -> list[str]:
    from secret_scan import path_is_blocked

    out = _git("ls-files")
    if out.returncode != 0:
        return []
    bad = []
    for line in out.stdout.splitlines():
        p = line.strip().replace("\\", "/")
        if p and path_is_blocked(p):
            bad.append(p)
    return bad


def repo_has_staged_secrets() -> tuple[list[str], list[str]]:
    sys.path.insert(0, str(ROOT / "scripts"))
    from secret_scan import scan_paths

    out = _git("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    staged = [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
    return scan_paths(staged, ROOT)


def assert_safe_to_push() -> None:
    """Raise SystemExit if secrets would reach GitHub."""
    tracked = repo_has_tracked_secrets()
    if tracked:
        print("BLOCKED: These secret files are TRACKED by git:\n  " + "\n  ".join(tracked))
        print("\nRun:  python scripts/untrack_secrets.py")
        print("Then: python scripts/purge_repo_secrets.py")
        raise SystemExit(1)

    blocked, content = repo_has_staged_secrets()
    if blocked or content:
        print("BLOCKED: Staged commit contains secrets.")
        for p in blocked:
            print(f"  path: {p}")
        for p in content:
            print(f"  {p}")
        raise SystemExit(1)

    # Block submodule pointer commits when MCP folder has dirty secret state
    if (ROOT / "MCPServer" / "saksham-mcp-server").exists():
        sub = _git("diff", "--cached", "--name-only", "MCPServer/saksham-mcp-server")
        if sub.stdout.strip():
            print(
                "BLOCKED: Do not commit MCPServer/saksham-mcp-server submodule changes.\n"
                "OAuth files belong in %LOCALAPPDATA%\\groww-insights\\ (outside repo)."
            )
            raise SystemExit(1)


if __name__ == "__main__":
    assert_safe_to_push()
    print("OK: safe to push.")
