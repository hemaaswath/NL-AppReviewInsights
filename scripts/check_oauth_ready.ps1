# Quick gate before Phase 3/4: OAuth outside repo + MCP health.

$RepoRoot = Split-Path $PSScriptRoot -Parent
$py = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "py" }
$ok = $true

$cred = & $py -c "import sys; sys.path.insert(0, r'$RepoRoot'); from shared.secret_paths import credentials_path; print(credentials_path())"
$token = & $py -c "import sys; sys.path.insert(0, r'$RepoRoot'); from shared.secret_paths import token_path; print(token_path())"

Write-Host "=== OAuth / MCP readiness ==="
Write-Host "Secrets dir (never in GitHub): $(Split-Path $cred -Parent)"

if (-not (Test-Path $cred)) {
    Write-Host "[FAIL] Missing credentials — run install_credentials.ps1"
    $ok = $false
} else {
    $projectId = (Get-Content $cred -Raw | ConvertFrom-Json).installed.project_id
    Write-Host "[OK] credentials project_id: $projectId"
}

if (-not (Test-Path $token)) {
    Write-Host "[FAIL] Missing token — run complete_oauth.ps1"
    $ok = $false
} else {
    Write-Host "[OK] token present (outside repo)"
}

& $py "$RepoRoot\scripts\purge_repo_secrets.py" | Out-Null

try {
    $h = Invoke-RestMethod "http://127.0.0.1:8000/health" -TimeoutSec 3
    Write-Host "[OK] MCP :8000 token=$($h.token_present)"
} catch {
    Write-Host "[WARN] MCP not on :8000 (optional for Streamlit Cloud)"
}

if ($ok) { exit 0 }
exit 1
