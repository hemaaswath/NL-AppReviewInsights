# One-time Google OAuth — token stored OUTSIDE repo (%LOCALAPPDATA%\groww-insights).
# Install credentials first: .\scripts\install_credentials.ps1 -SourcePath "path\to\credentials.json"

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$py = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "py" }
$McpRoot = Join-Path $Root "MCPServer\saksham-mcp-server"

$credExternal = & $py -c "import sys; sys.path.insert(0, r'$Root'); from shared.secret_paths import credentials_path; print(credentials_path())"
$tokenExternal = & $py -c "import sys; sys.path.insert(0, r'$Root'); from shared.secret_paths import token_path; print(token_path())"

if (-not (Test-Path $credExternal)) {
    Write-Error "Missing credentials at $credExternal. Run install_credentials.ps1 first."
}

if (-not (Test-Path $McpRoot)) {
    Write-Error "Missing MCP server. Clone: git clone https://github.com/saksham20189575/saksham-mcp-server.git $McpRoot"
}

Remove-Item Env:OAUTH_CONSOLE -ErrorAction SilentlyContinue
Set-Location $McpRoot

# auth.py reads credentials.json next to itself — temporary copy only for OAuth flow
Copy-Item -Path $credExternal -Destination (Join-Path $McpRoot "credentials.json") -Force

$usePasteCode = $args -contains "-PasteCode"
if ($usePasteCode) { $env:OAUTH_CONSOLE = "true" }

python auth.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (Test-Path "token.json") {
    Copy-Item -Path "token.json" -Destination $tokenExternal -Force
}

Set-Location $Root
& $py "$Root\scripts\purge_repo_secrets.py"

if (Test-Path $tokenExternal) {
    Write-Host "Success: token stored OUTSIDE repo at $tokenExternal"
    Write-Host "Repo folder contains no OAuth files safe for git push."
} else {
    Write-Error "token was not created."
}
