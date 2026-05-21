"""
Run Phase 2 analysis and save results to phase-2/test-results/.
"""
import sys
import json
import os
sys.path.insert(0, '.')
sys.path.insert(0, 'phase-2/src')

from analysis_orchestrator import AnalysisOrchestrator

os.makedirs('phase-2/test-results', exist_ok=True)

orch = AnalysisOrchestrator()
insights = orch.run()

# Save JSON output
output = orch.get_insights_json()
with open('phase-2/test-results/insights.json', 'w', encoding='utf-8') as f:
    f.write(output)

print("\nInsights saved to phase-2/test-results/insights.json")
orch.close()
