# Start saksham-mcp-server for Phase 3 (Docs) and Phase 4 (Gmail).
# Google Cloud project: Appreview — credentials.json + token.json in MCPServer/saksham-mcp-server (run auth.py once).

$McpRoot = Join-Path (Split-Path $PSScriptRoot -Parent) "MCPServer\saksham-mcp-server"
if (-not (Test-Path $McpRoot)) {
    Write-Error "Expected MCPServer\saksham-mcp-server with credentials.json"
    exit 1
}

Set-Location $McpRoot
$env:AUTO_APPROVE = "true"
Write-Host "Starting MCP at http://127.0.0.1:8000 (Ctrl+C to stop)"
python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload
