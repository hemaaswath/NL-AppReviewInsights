# Copy an existing token.json into MCPServer (e.g. from another machine).
param(
    [Parameter(Mandatory = $true)]
    [string]$SourcePath
)

$dest = Join-Path (Split-Path $PSScriptRoot -Parent) "MCPServer\saksham-mcp-server\token.json"
if (-not (Test-Path $SourcePath)) {
    Write-Error "Not found: $SourcePath"
    exit 1
}

Copy-Item -Path $SourcePath -Destination $dest -Force
Write-Host "Installed token -> $dest"
Write-Host "Restart MCP: .\scripts\start_mcp_server.ps1"
Write-Host "Then: .\scripts\check_oauth_ready.ps1"
