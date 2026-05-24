# Install pre-commit + pre-push hooks to block accidental secret commits/pushes.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$HooksDir = Join-Path $Root "scripts\git-hooks"
$GitHooks = Join-Path $Root ".git\hooks"

if (-not (Test-Path (Join-Path $Root ".git"))) {
    Write-Error "Not a git repo: $Root"
}

foreach ($name in @("pre-commit", "pre-push")) {
    $src = Join-Path $HooksDir $name
    $dest = Join-Path $GitHooks $name
    Copy-Item $src $dest -Force
    Write-Host "Installed $name -> $dest"
}

Write-Host ""
Write-Host "Blocked: .env, secrets.toml, token.json, credentials.json, gsk_/sk- keys in file content."
Write-Host "Before push:  python scripts/secret_scan.py tracked"
Write-Host "Safe push:    .\scripts\safe_git_push.ps1"
Write-Host "Untrack leaks: python scripts/untrack_secrets.py"
