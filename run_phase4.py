"""
Run Phase 4 distribution (Gmail draft via saksham-mcp-server).
"""
import sys
from pathlib import Path

import requests

sys.path.insert(0, ".")
sys.path.insert(0, "phase-4/src")

from shared.mcp_config import resolve_mcp_server_url
from distribution_orchestrator import DistributionOrchestrator

MCP_TOKEN = Path("MCPServer/saksham-mcp-server/token.json")


def _preflight() -> None:
    mcp_url = resolve_mcp_server_url()
    try:
        resp = requests.get(f"{mcp_url}/health", timeout=5)
        resp.raise_for_status()
        info = resp.json()
    except requests.exceptions.HTTPError:
        # Old MCP build without /health — probe draft endpoint must not hang.
        try:
            probe = requests.post(
                f"{mcp_url}/create_email_draft",
                json={"to": "probe@local", "subject": "probe", "body": "probe"},
                timeout=5,
            )
            probe.json()
        except requests.exceptions.Timeout:
            raise SystemExit(
                f"MCP at {mcp_url} is an old or misconfigured process (requests hang).\n"
                "Stop it (Ctrl+C), then start: .\\scripts\\start_mcp_server.ps1"
            ) from None
        except Exception:
            raise SystemExit(
                f"MCP at {mcp_url} is unreachable or outdated.\n"
                "Start: .\\scripts\\start_mcp_server.ps1"
            ) from None
        info = {}
    except Exception as exc:
        raise SystemExit(
            f"MCP server not reachable at {mcp_url}. "
            "Start it: .\\scripts\\start_mcp_server.ps1"
        ) from exc

    if info:
        if not info.get("http_handler_safe"):
            raise SystemExit(
                "MCP server is outdated (missing non-blocking HTTP fixes).\n"
                "Restart: .\\scripts\\start_mcp_server.ps1"
            )
        if not info.get("auto_approve"):
            raise SystemExit(
                "MCP server needs AUTO_APPROVE=true.\n"
                "Restart using: .\\scripts\\start_mcp_server.ps1"
            )
        project_id = info.get("credentials_project_id", "")
        if project_id == "nl-mylearning":
            raise SystemExit(
                f"MCP is using stale credentials (project_id=nl-mylearning).\n"
                f"Save Appreview credentials.json to:\n  {info.get('credentials_path', MCP_TOKEN.parent)}"
            )
        if not info.get("token_present"):
            raise SystemExit(
                f"MCP reports no token.json. Run OAuth:\n"
                f"  .\\scripts\\complete_oauth.ps1"
            )

    if not MCP_TOKEN.is_file():
        raise SystemExit(
            f"Missing {MCP_TOKEN}. Run OAuth first:\n"
            "  cd MCPServer\\saksham-mcp-server\n"
            "  python auth.py"
        )


_preflight()
orch = DistributionOrchestrator()
try:
    result = orch.run()
    print("\nPhase 4 result:")
    for key in ("week", "status", "message_id", "recipient", "doc_url", "source"):
        print(f"  {key}: {result.get(key)}")
finally:
    orch.close()
