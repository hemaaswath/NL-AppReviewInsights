# Install OAuth credentials OUTSIDE the repo (%LOCALAPPDATA%\groww-insights).
param(
    [Parameter(Mandatory = $true)]
    [string]$SourcePath
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$py = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "py" }

if (-not (Test-Path $SourcePath)) {
    Write-Error "Source not found: $SourcePath"
}

$dest = & $py -c "import sys; sys.path.insert(0, r'$Root'); from shared.secret_paths import credentials_path; print(credentials_path())"
New-Item -ItemType Directory -Force -Path (Split-Path $dest) | Out-Null
Copy-Item -Path $SourcePath -Destination $dest -Force

& $py "$Root\scripts\purge_repo_secrets.py" | Out-Null

Write-Host "Installed credentials OUTSIDE repo -> $dest"
Write-Host "This path is never committed to GitHub."
