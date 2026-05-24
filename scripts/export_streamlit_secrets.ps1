# Export OAuth token for Streamlit Cloud secrets — reads from OUTSIDE repo only.
param([switch]$IncludeCredentials)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$py = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "py" }

& $py "$Root\scripts\purge_repo_secrets.py" | Out-Null

$TokenPath = & $py -c "import sys; sys.path.insert(0, r'$Root'); from shared.secret_paths import token_path; print(token_path())"
$CredsPath = & $py -c "import sys; sys.path.insert(0, r'$Root'); from shared.secret_paths import credentials_path; print(credentials_path())"

if (-not (Test-Path $TokenPath)) {
    Write-Error "Missing token at $TokenPath — run .\scripts\complete_oauth.ps1 first."
}

$out = @"
# DO NOT COMMIT — paste into Streamlit Cloud -> Settings -> Secrets ONLY
# Never add this file to GitHub.

GROQ_API_KEY = "YOUR_GROQ_KEY"
GOOGLE_PLAY_PACKAGE_NAME = "com.nextbillion.groww"
GOOGLE_DOC_ID = "YOUR_DOC_ID"
EMAIL_RECIPIENT = "your@gmail.com"
DATABASE_PATH = "data/reviews.db"

GOOGLE_TOKEN_JSON = '$((Get-Content $TokenPath -Raw).Trim() -replace "'", "''")'
"@

if ($IncludeCredentials -and (Test-Path $CredsPath)) {
    $credsRaw = (Get-Content $CredsPath -Raw).Trim()
    $out += "`n`nGOOGLE_CREDENTIALS_JSON = '$($credsRaw -replace "'", "''")'"
}

$dest = Join-Path $Root ".streamlit\secrets_export.txt"
$out | Set-Content -Path $dest -Encoding utf8
Write-Host "Wrote $dest (gitignored)"
Write-Host "Paste into Streamlit Cloud Secrets — NOT GitHub."
