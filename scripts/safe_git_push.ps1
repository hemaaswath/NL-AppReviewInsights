# Scan repo then push — refuses if secrets are staged, in commits, or in tracked files.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

& "$Root\scripts\install_git_hooks.ps1" | Out-Null

$py = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "py" }
& $py "$Root\scripts\secret_scan.py" staged
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $py "$Root\scripts\secret_scan.py" tracked
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $py "$Root\scripts\purge_repo_secrets.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $py "$Root\scripts\repo_git_guard.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Scan OK. Pushing to origin..."
git push origin HEAD
exit $LASTEXITCODE
