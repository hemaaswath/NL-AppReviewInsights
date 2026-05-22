# Fail if git staging area contains secret files (run before git commit).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$blockedPatterns = @(
    "\.env$",
    "secrets\.toml$",
    "secrets_export",
    "token\.json$",
    "credentials\.json$",
    "oauth_authorize_url"
)

$staged = git diff --cached --name-only 2>$null
if (-not $staged) { Write-Host "No staged files."; exit 0 }

$bad = @()
foreach ($file in $staged) {
    foreach ($pat in $blockedPatterns) {
        if ($file -match $pat) { $bad += $file; break }
    }
}

if ($bad.Count -gt 0) {
    Write-Error @"
Refusing to proceed: secret files are staged for commit:
$($bad -join "`n")

Unstage them:  git reset HEAD -- <file>
Secrets belong in:
  - Local: .env (gitignored) and MCPServer/saksham-mcp-server/token.json (gitignored)
  - Cloud: Streamlit app Settings -> Secrets (NOT in the GitHub repo)
"@
}
Write-Host "OK: no secret files staged."
