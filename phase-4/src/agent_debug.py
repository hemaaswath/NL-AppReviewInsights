"""NDJSON debug logging for Phase 4 (session 2777b3)."""
import json
import os
import time
from typing import Any, Optional

_LOG = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "debug-2777b3.log")
)
_SESSION = "2777b3"


def agent_log(
    location: str,
    message: str,
    data: Optional[dict[str, Any]] = None,
    *,
    hypothesis_id: str = "",
    run_id: str = "pre-fix",
) -> None:
    # region agent log
    try:
        payload = {
            "sessionId": _SESSION,
            "runId": run_id,
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000),
        }
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, default=str) + "\n")
    except OSError:
        pass
    # endregion
