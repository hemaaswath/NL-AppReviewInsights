"""
Scan git paths and file contents for secrets before commit/push.
Used by pre-commit, pre-push, and CI.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# Paths that must never be committed (matched anywhere in path, forward slashes)
BLOCKED_PATH_RE = re.compile(
    r"(?:^|/)(?:\.env(?:\.|$)|secrets\.toml$|secrets_export|token\.json$|"
    r"credentials\.json$|oauth_authorize_url\.txt$|\.oauth_client_id$|"
    r"service[_-]?account.*\.json$|\.pem$|\.p12$)(?:/|$)|"
    r"/\.env\.|/secrets\.toml$",
    re.I,
)

# Safe paths: examples and docs placeholders only
SAFE_PATH_SUFFIXES = (
    ".example",
    ".example.md",
    "secrets.toml.example",
    "SECRETS_AND_GIT.md",
    "check_no_secrets_staged",
    "secret_scan.py",
    "install_git_hooks",
    "export_streamlit_secrets.ps1",
)

# Content patterns (real secrets — not placeholders like "your_groq_key")
CONTENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Groq API key (gsk_...)", re.compile(r"gsk_[A-Za-z0-9]{20,}")),
    ("OpenAI-style key (sk-...)", re.compile(r"sk-[A-Za-z0-9]{20,}")),
    ("Google API key (AIza...)", re.compile(r"AIza[A-Za-z0-9_-]{30,}")),
    (
        "OAuth refresh_token value",
        re.compile(r'"refresh_token"\s*:\s*"(?!\.{3}|YOUR|your|xxx)[A-Za-z0-9_/-]{15,}"'),
    ),
    (
        "OAuth client_secret value",
        re.compile(
            r'"client_secret"\s*:\s*"(?!\.{3}|YOUR|your|xxx)[A-Za-z0-9_/-]{15,}"'
        ),
    ),
    (
        "GOOGLE_TOKEN_JSON with embedded JSON",
        re.compile(
            r'GOOGLE_TOKEN_JSON\s*=\s*["\']?\{[^"\']{80,}["\']?',
            re.I,
        ),
    ),
]


def _is_safe_path(path: str) -> bool:
    p = path.replace("\\", "/")
    if any(s in p for s in SAFE_PATH_SUFFIXES):
        return True
    if p.endswith(".md") and "refresh_token" in p and ".example" in p:
        return True
    return False


def path_is_blocked(path: str) -> bool:
    if _is_safe_path(path):
        return False
    return bool(BLOCKED_PATH_RE.search(path.replace("\\", "/")))


def scan_file_content(path: str, text: str) -> list[str]:
    if _is_safe_path(path):
        return []
    hits: list[str] = []
    for label, pattern in CONTENT_PATTERNS:
        if pattern.search(text):
            hits.append(label)
    return hits


def git_staged_files() -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        capture_output=True,
        text=True,
        check=False,
    )
    return [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]


def git_files_in_push() -> list[str]:
    """Files that differ between upstream and HEAD (for pre-push)."""
    out = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "@{u}"],
        capture_output=True,
        text=True,
        check=False,
    )
    upstream = out.stdout.strip()
    if not upstream or out.returncode != 0:
        return git_staged_files()
    diff = subprocess.run(
        ["git", "diff", "--name-only", f"{upstream}..HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return [ln.strip() for ln in diff.stdout.splitlines() if ln.strip()]


def scan_paths(paths: list[str], root: Path | None = None) -> tuple[list[str], list[str]]:
    """Return (blocked_paths, content_violations as 'path: reason')."""
    root = root or Path.cwd()
    blocked: list[str] = []
    content_bad: list[str] = []

    for rel in paths:
        if path_is_blocked(rel):
            blocked.append(rel)
            continue
        full = root / rel
        if not full.is_file():
            continue
        try:
            text = full.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for hit in scan_file_content(rel, text):
            content_bad.append(f"{rel}: {hit}")
    return blocked, content_bad


def main(argv: list[str] | None = None) -> int:
    mode = (argv or sys.argv[1:2] or ["staged"])[0]
    root = Path.cwd()

    if mode == "tracked":
        out = subprocess.run(
            ["git", "ls-files"],
            capture_output=True,
            text=True,
            check=False,
        )
        paths = [ln.strip() for ln in out.stdout.splitlines() if ln.strip()]
    elif mode == "push":
        paths = git_files_in_push()
    else:
        paths = git_staged_files()

    if not paths:
        print("OK: nothing to scan.")
        return 0

    blocked, content_bad = scan_paths(paths, root)
    if blocked:
        print("BLOCKED PATHS (never commit):")
        for p in blocked:
            print(f"  {p}")
    if content_bad:
        print("BLOCKED CONTENT (secrets detected in file body):")
        for p in content_bad:
            print(f"  {p}")
    if blocked or content_bad:
        print(
            "\nFix: git reset HEAD -- <file>  |  keep secrets in .env and Streamlit Cloud UI only"
        )
        print("Run: .\\scripts\\install_git_hooks.ps1")
        return 1
    print(f"OK: scanned {len(paths)} file(s), no secrets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
