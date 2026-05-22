"""
App Review Insights Analyzer — Streamlit Cloud UI.

Deploy on https://share.streamlit.io with this file as the main entrypoint.
Phases 3–4 use direct Google APIs (no separate MCP server on Railway).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "phase-1" / "src"))
sys.path.insert(0, str(ROOT / "phase-2" / "src"))
sys.path.insert(0, str(ROOT / "phase-3" / "src"))
sys.path.insert(0, str(ROOT / "phase-4" / "src"))

os.environ.setdefault("STREAMLIT_DEPLOYMENT", "1")
os.environ.setdefault("USE_DIRECT_GOOGLE", "1")

import streamlit as st
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

SECRET_KEYS = (
    "GROQ_API_KEY",
    "GOOGLE_PLAY_PACKAGE_NAME",
    "GOOGLE_DOC_ID",
    "EMAIL_RECIPIENT",
    "DATABASE_PATH",
    "GOOGLE_TOKEN_JSON",
    "GOOGLE_CREDENTIALS_JSON",
)


def apply_streamlit_secrets() -> None:
    """Map Streamlit Cloud secrets into os.environ."""
    try:
        for key in SECRET_KEYS:
            if key in st.secrets and st.secrets[key]:
                os.environ[key] = str(st.secrets[key])
    except Exception:
        pass


apply_streamlit_secrets()

st.set_page_config(
    page_title="Groww Review Insights",
    page_icon="📊",
    layout="wide",
)

st.title("App Review Insights Analyzer")
st.caption("Phases 1–4: collect → analyze → Google Doc → Gmail draft (direct Google API on Streamlit)")

from shared.google_auth import credentials_status

status = credentials_status()
col1, col2, col3 = st.columns(3)
col1.metric("Google token", "OK" if status["token_present"] else "Missing")
col2.metric("GCP project", status.get("credentials_project_id") or "—")
col3.metric("Mode", "Streamlit direct API")

with st.expander("Configuration", expanded=not status["token_present"]):
    st.markdown(
        """
Set secrets in **Streamlit Cloud → App settings → Secrets** (see `Docs/DEPLOYMENT_STREAMLIT.md`).
Locally: copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.
        """
    )
    st.json(
        {
            "GOOGLE_DOC_ID": bool(os.getenv("GOOGLE_DOC_ID")),
            "EMAIL_RECIPIENT": os.getenv("EMAIL_RECIPIENT", ""),
            "GROQ_API_KEY": bool(os.getenv("GROQ_API_KEY")),
            "DATABASE_PATH": os.getenv("DATABASE_PATH", "data/reviews.db"),
        }
    )


def run_collect_inline():
    """Run collection (run_gp_collect has no main — exec module body)."""
    import subprocess

    subprocess.run([sys.executable, str(ROOT / "run_gp_collect.py")], check=True, cwd=ROOT)


def run_phase2():
    from analysis_orchestrator import AnalysisOrchestrator

    orch = AnalysisOrchestrator()
    try:
        return orch.run()
    finally:
        orch.close()


def run_phase3():
    from report_orchestrator import ReportOrchestrator

    os.makedirs(ROOT / "phase-3" / "test-results", exist_ok=True)
    orch = ReportOrchestrator()
    try:
        return orch.run()
    finally:
        orch.close()


def run_phase4():
    from distribution_orchestrator import DistributionOrchestrator

    orch = DistributionOrchestrator()
    try:
        return orch.run()
    finally:
        orch.close()


def show_insights():
    from shared.database import DatabaseManager

    db_path = os.getenv("DATABASE_PATH", "data/reviews.db")
    db = DatabaseManager(db_path)
    try:
        insights = db.get_insights()
        if insights:
            st.subheader("Latest insights")
            st.json(
                {
                    k: insights.get(k)
                    for k in ("week", "doc_id", "doc_url", "email_id", "source")
                    if insights.get(k) is not None
                }
            )
        else:
            st.info("No insights in the database yet. Run Phase 2 first.")
    finally:
        db.close()


tab_run, tab_status = st.tabs(["Run pipeline", "Database"])

with tab_run:
    st.markdown("Run steps in order. Phase 1 can take several minutes.")

    if st.button("Phase 1 — Collect Google Play reviews", type="primary"):
        with st.spinner("Collecting reviews…"):
            run_collect_inline()
        st.success("Phase 1 complete.")

    if st.button("Phase 2 — Analyze (Groq)"):
        with st.spinner("Running analysis…"):
            result = run_phase2()
        st.success("Phase 2 complete.")
        st.json(result if isinstance(result, dict) else {"status": "ok"})

    if st.button("Phase 3 — Append report to Google Doc"):
        with st.spinner("Writing to Google Doc…"):
            result = run_phase3()
        st.success("Phase 3 complete.")
        st.json(result)

    if st.button("Phase 4 — Create Gmail draft"):
        with st.spinner("Creating Gmail draft…"):
            result = run_phase4()
        st.success("Phase 4 complete.")
        st.json(result)

    if st.button("Run full pipeline (1 → 4)", type="secondary"):
        with st.status("Full pipeline", expanded=True) as s:
            s.write("Phase 1: collecting…")
            run_collect_inline()
            s.write("Phase 2: analyzing…")
            run_phase2()
            s.write("Phase 3: Google Doc…")
            run_phase3()
            s.write("Phase 4: Gmail draft…")
            run_phase4()
            s.update(label="Pipeline complete", state="complete")
        st.balloons()

with tab_status:
    show_insights()
