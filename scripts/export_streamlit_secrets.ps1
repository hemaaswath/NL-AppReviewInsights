# Export OAuth token (and optional credentials) for Streamlit Cloud secrets.
# Run from repo root after complete_oauth.ps1.

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Mcp = Join-Path $Root "MCPServer\saksham-mcp-server"
$TokenPath = Join-Path $Mcp "token.json"
$CredsPath = Join-Path $Mcp "credentials.json"

if (-not (Test-Path $TokenPath)) {
    Write-Error "Missing $TokenPath — run .\scripts\complete_oauth.ps1 first."
}

$out = @"
# Paste into Streamlit Cloud → Secrets (or .streamlit/secrets.toml locally)

GROQ_API_KEY = "YOUR_GROQ_KEY"
GOOGLE_PLAY_PACKAGE_NAME = "com.groww"
GOOGLE_DOC_ID = "YOUR_DOC_ID"
EMAIL_RECIPIENT = "your@gmail.com"
DATABASE_PATH = "data/reviews.db"

# Single-quoted TOML so inner JSON double-quotes are safe on Streamlit Cloud
GOOGLE_TOKEN_JSON = '$((Get-Content $TokenPath -Raw).Trim() -replace "'", "''")'
"@

if (Test-Path $CredsPath) {
    $credsRaw = (Get-Content $CredsPath -Raw).Trim()
    $out += "`n`nGOOGLE_CREDENTIALS_JSON = '$($credsRaw -replace "'", "''")'"
}

$dest = Join-Path $Root ".streamlit\secrets_export.txt"
$out | Set-Content -Path $dest -Encoding utf8
Write-Host "Wrote $dest"
Write-Host "Copy GOOGLE_TOKEN_JSON and other keys into Streamlit Cloud secrets."
