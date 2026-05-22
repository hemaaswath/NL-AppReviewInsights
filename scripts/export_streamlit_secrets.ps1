# Export OAuth token for Streamlit Cloud secrets (local file only — NEVER commit output).
# Run from repo root after complete_oauth.ps1.

param([switch]$IncludeCredentials)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Mcp = Join-Path $Root "MCPServer\saksham-mcp-server"
$TokenPath = Join-Path $Mcp "token.json"
$CredsPath = Join-Path $Mcp "credentials.json"

if (-not (Test-Path $TokenPath)) {
    Write-Error "Missing $TokenPath — run .\scripts\complete_oauth.ps1 first."
}

$out = @"
# DO NOT COMMIT THIS FILE — paste into Streamlit Cloud → App settings → Secrets only
# File is gitignored: .streamlit/secrets_export.txt

GROQ_API_KEY = "YOUR_GROQ_KEY"
GOOGLE_PLAY_PACKAGE_NAME = "com.nextbillion.groww"
GOOGLE_DOC_ID = "YOUR_DOC_ID"
EMAIL_RECIPIENT = "your@gmail.com"
DATABASE_PATH = "data/reviews.db"

# Single-quoted TOML so inner JSON double-quotes are safe on Streamlit Cloud
GOOGLE_TOKEN_JSON = '$((Get-Content $TokenPath -Raw).Trim() -replace "'", "''")'
"@

if ($IncludeCredentials -and (Test-Path $CredsPath)) {
    $credsRaw = (Get-Content $CredsPath -Raw).Trim()
    $out += "`n`nGOOGLE_CREDENTIALS_JSON = '$($credsRaw -replace "'", "''")'"
}

$dest = Join-Path $Root ".streamlit\secrets_export.txt"
$out | Set-Content -Path $dest -Encoding utf8
Write-Host "Wrote $dest (gitignored — do NOT add or push to GitHub)"
Write-Host "Paste values into: https://share.streamlit.io -> your app -> Settings -> Secrets"
Write-Host "Do NOT create .streamlit/secrets.toml in the repo for Cloud deploy."
