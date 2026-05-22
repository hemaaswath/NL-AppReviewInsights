# Install pre-commit hook to block accidental secret commits.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$HookSrc = Join-Path $Root "scripts\git-hooks\pre-commit"
$HookDest = Join-Path $Root ".git\hooks\pre-commit"

if (-not (Test-Path (Join-Path $Root ".git"))) {
    Write-Error "Not a git repo: $Root"
}

Copy-Item $HookSrc $HookDest -Force
Write-Host "Installed pre-commit hook -> $HookDest"
Write-Host "Commits that stage .env, secrets.toml, token.json, etc. will be blocked."
