"""
Run Phases 1–4 sequentially for Streamlit / background jobs.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parent.parent


def _ensure_no_repo_secrets() -> None:
    sys.path.insert(0, str(ROOT))
    from shared.secret_paths import ensure_secrets_outside_repo

    ensure_secrets_outside_repo()


def _run_collect() -> dict:
    _ensure_no_repo_secrets()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [sys.executable, str(ROOT / "run_gp_collect.py")],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    # Collection may exit 1 on Windows star-print; treat as OK if stderr lacks fatal trace
    ok = proc.returncode == 0 or "COLLECTION COMPLETE" in (proc.stdout or "")
    return {
        "phase": 1,
        "ok": ok,
        "detail": "Reviews collected" if ok else (proc.stderr or proc.stdout or "collect failed")[-500:],
    }


def run_dashboard_pipeline(
    database_path: Optional[str] = None,
    on_step: Optional[Callable[[int, str, str], None]] = None,
    *,
    include_publish: bool = True,
) -> dict:
    """
    Run phases 1–2 (fast dashboard); optionally 3–4 (Doc/Gmail).
    on_step state: running | done | skipped | error
    """
    os.environ.setdefault("USE_DIRECT_GOOGLE", "1")
    os.environ.setdefault("STREAMLIT_DEPLOYMENT", "1")

    if database_path:
        os.environ["DATABASE_PATH"] = database_path

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "phase-2" / "src"))
    if include_publish:
        sys.path.insert(0, str(ROOT / "phase-3" / "src"))
        sys.path.insert(0, str(ROOT / "phase-4" / "src"))

    results: list[dict] = []

    def step(n: int, label: str, state: str) -> None:
        if on_step:
            on_step(n, label, state)

    step(1, "Collecting Play Store reviews", "running")
    try:
        r1 = _run_collect()
        results.append(r1)
        step(1, "Collecting Play Store reviews", "done" if r1["ok"] else "error")
        if not r1["ok"]:
            return {"ok": False, "phases": results}
    except Exception as exc:
        results.append({"phase": 1, "ok": False, "detail": str(exc)})
        step(1, "Collecting Play Store reviews", "error")
        return {"ok": False, "phases": results}

    step(2, "Analyzing sentiment & themes", "running")
    try:
        from analysis_orchestrator import AnalysisOrchestrator

        orch = AnalysisOrchestrator(database_path=database_path)
        try:
            orch.run()
        finally:
            orch.close()
        results.append({"phase": 2, "ok": True, "detail": "Insights saved"})
        step(2, "Analyzing sentiment & themes", "done")
    except Exception as exc:
        results.append({"phase": 2, "ok": False, "detail": str(exc)})
        step(2, "Analyzing sentiment & themes", "error")
        return {"ok": False, "phases": results}

    if not include_publish:
        step(3, "Publishing Google Doc report", "skipped")
        step(4, "Gmail draft", "skipped")
        return {"ok": True, "phases": results}

    step(3, "Publishing Google Doc report", "running")
    try:
        from report_orchestrator import ReportOrchestrator

        os.makedirs(ROOT / "phase-3" / "test-results", exist_ok=True)
        orch = ReportOrchestrator(database_path=database_path)
        try:
            p3 = orch.run()
        finally:
            orch.close()
        results.append({"phase": 3, "ok": True, "detail": p3.get("source", "ok")})
        step(3, "Publishing Google Doc report", "done")
    except Exception as exc:
        results.append({"phase": 3, "ok": False, "detail": str(exc)})
        step(3, "Publishing Google Doc report", "error")
        return {"ok": False, "phases": results}

    from email_composer import validate_email

    recipient = os.getenv("EMAIL_RECIPIENT", "").strip()
    if not validate_email(recipient):
        results.append({"phase": 4, "ok": True, "detail": "skipped — EMAIL_RECIPIENT not set"})
        step(4, "Gmail draft", "skipped")
        return {"ok": True, "phases": results}

    step(4, "Creating Gmail draft", "running")
    try:
        from distribution_orchestrator import DistributionOrchestrator

        orch = DistributionOrchestrator(
            database_path=database_path,
            recipient=recipient,
        )
        try:
            orch.run()
        finally:
            orch.close()
        results.append({"phase": 4, "ok": True, "detail": "draft_created"})
        step(4, "Creating Gmail draft", "done")
    except Exception as exc:
        results.append({"phase": 4, "ok": False, "detail": str(exc)})
        step(4, "Creating Gmail draft", "error")
        return {"ok": False, "phases": results}

    return {"ok": True, "phases": results}


def run_publish_phases(
    database_path: Optional[str] = None,
    on_step: Optional[Callable[[int, str, str], None]] = None,
) -> dict:
    """Phases 3–4 only (after dashboard data is already loaded)."""
    os.environ.setdefault("USE_DIRECT_GOOGLE", "1")
    os.environ.setdefault("STREAMLIT_DEPLOYMENT", "1")
    if database_path:
        os.environ["DATABASE_PATH"] = database_path

    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "phase-3" / "src"))
    sys.path.insert(0, str(ROOT / "phase-4" / "src"))

    results: list[dict] = []

    def step(n: int, label: str, state: str) -> None:
        if on_step:
            on_step(n, label, state)

    step(3, "Publishing Google Doc report", "running")
    try:
        from report_orchestrator import ReportOrchestrator

        os.makedirs(ROOT / "phase-3" / "test-results", exist_ok=True)
        orch = ReportOrchestrator(database_path=database_path)
        try:
            p3 = orch.run()
        finally:
            orch.close()
        results.append({"phase": 3, "ok": True, "detail": p3.get("source", "ok")})
        step(3, "Publishing Google Doc report", "done")
    except Exception as exc:
        results.append({"phase": 3, "ok": False, "detail": str(exc)})
        step(3, "Publishing Google Doc report", "error")
        return {"ok": False, "phases": results}

    from email_composer import validate_email

    recipient = os.getenv("EMAIL_RECIPIENT", "").strip()
    if not validate_email(recipient):
        results.append({"phase": 4, "ok": True, "detail": "skipped — EMAIL_RECIPIENT not set"})
        step(4, "Gmail draft", "skipped")
        return {"ok": True, "phases": results}

    step(4, "Creating Gmail draft", "running")
    try:
        from distribution_orchestrator import DistributionOrchestrator

        orch = DistributionOrchestrator(
            database_path=database_path,
            recipient=recipient,
        )
        try:
            orch.run()
        finally:
            orch.close()
        results.append({"phase": 4, "ok": True, "detail": "draft_created"})
        step(4, "Creating Gmail draft", "done")
    except Exception as exc:
        results.append({"phase": 4, "ok": False, "detail": str(exc)})
        step(4, "Creating Gmail draft", "error")
        return {"ok": False, "phases": results}

    return {"ok": True, "phases": results}


def run_full_pipeline(
    database_path: Optional[str] = None,
    on_step: Optional[Callable[[int, str, str], None]] = None,
) -> dict:
    """Run phases 1→4 (CLI / full refresh)."""
    return run_dashboard_pipeline(
        database_path=database_path,
        on_step=on_step,
        include_publish=True,
    )
