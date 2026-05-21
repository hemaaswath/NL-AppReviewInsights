# Print Google OAuth URL only (no browser). Use with complete_oauth.ps1 paste-code flow.

$McpRoot = Join-Path (Split-Path $PSScriptRoot -Parent) "MCPServer\saksham-mcp-server"
Set-Location $McpRoot

$env:OAUTH_CONSOLE = "true"
python -c @"
import os
os.environ.pop('MCP_HTTP_HANDLER', None)
from auth import CREDENTIALS_PATH, SCOPES, credentials_meta, _run_manual_oauth
from google_auth_oauthlib.flow import InstalledAppFlow

meta = credentials_meta()
print('project_id:', meta.get('project_id'))
print('client_id : ...' + meta.get('client_id', '')[-24:])
print()
print('Add this Gmail under GCP OAuth Test users if you see 403 access_denied:')
print('  hemaaswath19@gmail.com (or your sign-in account)')
print()
flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
print('Open this URL, authorize, then run:')
print('  .\\scripts\\complete_oauth.ps1')
print()
print(auth_url)
"@
