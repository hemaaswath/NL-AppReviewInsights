"""Remove secret files from repo tree; migrate OAuth to %LOCALAPPDATA%\\groww-insights."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.secret_paths import ensure_secrets_outside_repo, local_secrets_dir, migrate_legacy_secrets, purge_secret_files_from_repo


def main() -> int:
    migrated = migrate_legacy_secrets()
    removed = purge_secret_files_from_repo()
    if migrated:
        print("Migrated to (outside repo):")
        for line in migrated:
            print(f"  {line}")
    if removed:
        print("Removed from repo folder:")
        for line in removed:
            print(f"  {line}")
    if not migrated and not removed:
        print("OK: no secret files in repo tree.")
    print(f"OAuth storage: {local_secrets_dir()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
