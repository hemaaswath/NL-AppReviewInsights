"""
Run Phase 3 report generation and save doc_id to the database.
"""
import sys
import os

sys.path.insert(0, ".")
sys.path.insert(0, "phase-3/src")

from report_orchestrator import ReportOrchestrator

os.makedirs("phase-3/test-results", exist_ok=True)

orch = ReportOrchestrator()
try:
    result = orch.run()
    print("\nPhase 3 result:")
    for key in ("week", "doc_id", "doc_url", "source", "word_count"):
        print(f"  {key}: {result.get(key)}")
finally:
    orch.close()
