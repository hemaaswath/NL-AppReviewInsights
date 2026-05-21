# One-time Google OAuth for saksham-mcp-server (creates token.json).
# Use Appreview GCP Desktop credentials in MCPServer\saksham-mcp-server\credentials.json

# Always start clean so a previous paste-code run does not force OAUTH_CONSOLE.
Remove-Item Env:OAUTH_CONSOLE -ErrorAction SilentlyContinue

$McpRoot = Join-Path (Split-Path $PSScriptRoot -Parent) "MCPServer\saksham-mcp-server"
Set-Location $McpRoot

if (-not (Test-Path "credentials.json")) {
    Write-Error "Missing credentials.json in $McpRoot"
    exit 1
}

$credPath = (Resolve-Path "credentials.json").Path
$meta = Get-Content $credPath -Raw | ConvertFrom-Json
$projectId = $meta.installed.project_id
Write-Host "Credentials file: $credPath"
Write-Host "GCP project_id: $projectId"
if ($projectId -eq "nl-mylearning") {
    Write-Error "credentials.json still has project_id nl-mylearning. Save Appreview OAuth JSON to: $credPath"
    exit 1
}
Write-Host ""
Write-Host "Sign in with a Gmail listed under Appreview OAuth Test users."
Write-Host ""

# Browser mode is default (paste-code URLs get truncated in Cursor terminals -> 400 invalid_request).
$usePasteCode = $args -contains "-PasteCode"
if ($usePasteCode) {
    $env:OAUTH_CONSOLE = "true"
    Write-Host "Mode: paste-code (URL also saved to oauth_authorize_url.txt)"
} else {
    Remove-Item Env:OAUTH_CONSOLE -ErrorAction SilentlyContinue
    Write-Host "Mode: browser (recommended - auto-captures code; keep this terminal open)"
    Write-Host "       Use -PasteCode only if browser mode fails."
}
Write-Host ""

python auth.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (Test-Path "token.json") {
    Write-Host ""
    Write-Host "Success: token.json created. Restart MCP: ..\..\scripts\start_mcp_server.ps1"
} else {
    Write-Error "token.json was not created. Complete the browser flow and re-run."
    exit 1
}
