# MCP server (optional, local only)

The [saksham-mcp-server](https://github.com/saksham20189575/saksham-mcp-server) is **not part of this git repo**.

Clone it locally if you use MCP (Phases 3–4 on your machine):

```powershell
git clone https://github.com/saksham20189575/saksham-mcp-server.git MCPServer/saksham-mcp-server
```

**OAuth files (`credentials.json`, `token.json`) must never live in this project folder.**

Store them only in:

- **Windows:** `%LOCALAPPDATA%\groww-insights\`
- **Streamlit Cloud:** App → Settings → Secrets (not GitHub)

Setup: see [Docs/MCP_SETUP.md](../Docs/MCP_SETUP.md).
