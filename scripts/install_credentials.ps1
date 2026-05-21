# Copy Google OAuth credentials.json into the MCP folder used by this repo.
param(
    [Parameter(Mandatory = $true)]
    [string]$SourcePath
)

$McpRoot = Join-Path (Split-Path $PSScriptRoot -Parent) "MCPServer\saksham-mcp-server"
$dest = Join-Path $McpRoot "credentials.json"

if (-not (Test-Path $SourcePath)) {
    Write-Error "Source not found: $SourcePath"
    exit 1
}

$meta = Get-Content $SourcePath -Raw | ConvertFrom-Json
$projectId = $meta.installed.project_id
if ($projectId -eq "nl-mylearning") {
    Write-Error "Refusing to install nl-mylearning credentials. Use Appreview OAuth JSON."
    exit 1
}

Copy-Item -Path $SourcePath -Destination $dest -Force

# Common mistake: duplicate clone at Documents\Nextleap\saksham-mcp-server
$legacy = Join-Path (Split-Path $PSScriptRoot -Parent | Split-Path -Parent) "saksham-mcp-server\credentials.json"
if ((Resolve-Path $SourcePath).Path -eq (Resolve-Path $legacy -ErrorAction SilentlyContinue).Path) {
    Write-Host "Note: copied from legacy path Nextleap\saksham-mcp-server (not used by this repo)."
}

if (Test-Path (Join-Path $McpRoot "token.json")) {
    Remove-Item (Join-Path $McpRoot "token.json") -Force
    Write-Host "Removed old token.json (re-run OAuth after client change)."
}
if (Test-Path (Join-Path $McpRoot ".oauth_client_id")) {
    Remove-Item (Join-Path $McpRoot ".oauth_client_id") -Force
}

Write-Host "Installed credentials -> $dest"
Write-Host "project_id: $projectId"
Write-Host "Next: .\scripts\complete_oauth.ps1"
