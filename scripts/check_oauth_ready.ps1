# Quick gate before Phase 3/4: credentials + token + MCP health.

$RepoRoot = Split-Path $PSScriptRoot -Parent
$McpRoot = Join-Path $RepoRoot "MCPServer\saksham-mcp-server"
$ok = $true

Write-Host "=== OAuth / MCP readiness ==="

$cred = Join-Path $McpRoot "credentials.json"
$token = Join-Path $McpRoot "token.json"

if (-not (Test-Path $cred)) {
    Write-Host "[FAIL] Missing $cred"
    $ok = $false
} else {
    $projectId = (Get-Content $cred -Raw | ConvertFrom-Json).installed.project_id
    if ($projectId -eq "nl-mylearning") {
        Write-Host "[FAIL] credentials project_id: $projectId (need Appreview)"
        $ok = $false
    } else {
        Write-Host "[OK] credentials project_id: $projectId"
    }
}

if (-not (Test-Path $token)) {
    Write-Host "[FAIL] Missing token.json - run: .\scripts\complete_oauth.ps1"
    Write-Host "      If browser shows 403 access_denied: GCP Appreview -> OAuth -> Test users -> add hemaaswath19@gmail.com"
    $ok = $false
} else {
    Write-Host "[OK] token.json present"
}

try {
    $h = Invoke-RestMethod "http://127.0.0.1:8000/health" -TimeoutSec 3
    Write-Host "[OK] MCP :8000 auto_approve=$($h.auto_approve) token=$($h.token_present) project=$($h.credentials_project_id)"
    if (-not $h.auto_approve) {
        Write-Host "[FAIL] MCP needs AUTO_APPROVE - use .\scripts\start_mcp_server.ps1"
        $ok = $false
    }
    if (-not $h.token_present) {
        Write-Host "[FAIL] MCP sees no token - restart MCP after OAuth"
        $ok = $false
    }
} catch {
    Write-Host "[FAIL] MCP not on :8000 - run .\scripts\start_mcp_server.ps1"
    $ok = $false
}

if ($ok) {
    Write-Host ""
    Write-Host "Ready for python run_phase4.py"
    exit 0
}
Write-Host ""
Write-Host "Not ready yet. Fix [FAIL] items above."
exit 1
