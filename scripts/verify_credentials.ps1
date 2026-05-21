# Print which credentials.json the MCP server will use (absolute path + project_id).

$RepoRoot = Split-Path $PSScriptRoot -Parent
$McpRoot = Join-Path $RepoRoot "MCPServer\saksham-mcp-server"
$credPath = Join-Path $McpRoot "credentials.json"
$legacyPath = Join-Path (Split-Path $RepoRoot -Parent) "saksham-mcp-server\credentials.json"

if (-not (Test-Path $credPath)) {
    Write-Error "Not found: $credPath"
    exit 1
}

$meta = Get-Content $credPath -Raw | ConvertFrom-Json
$projectId = $meta.installed.project_id
$clientSuffix = $meta.installed.client_id.Substring([Math]::Max(0, $meta.installed.client_id.Length - 24))

Write-Host "Path      : $credPath"
Write-Host "project_id: $projectId"
Write-Host "client_id : ...$clientSuffix"
Write-Host "Modified  : $((Get-Item $credPath).LastWriteTime)"

if (Test-Path $legacyPath) {
    $legacyMeta = Get-Content $legacyPath -Raw | ConvertFrom-Json
    $legacyProject = $legacyMeta.installed.project_id
    Write-Host ""
    Write-Host "Legacy path (NOT used by pipeline): $legacyPath"
    Write-Host "legacy project_id: $legacyProject"
    if ($legacyProject -ne $projectId) {
        Write-Host "WARNING: legacy folder has different credentials. Run:"
        Write-Host "  .\scripts\install_credentials.ps1 -SourcePath `"$legacyPath`""
    }
}

try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -TimeoutSec 3
    Write-Host ""
    Write-Host "MCP /health credentials_project_id: $($health.credentials_project_id)"
    Write-Host "MCP /health credentials_path       : $($health.credentials_path)"
} catch {
    Write-Host ""
    Write-Host "MCP not running on :8000 (start scripts/start_mcp_server.ps1 to compare live server)"
}
