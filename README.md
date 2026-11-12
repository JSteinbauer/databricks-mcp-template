# Databricks MCP Server Template

A minimal [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server built with
[FastMCP](https://gofastmcp.com) and FastAPI, deployable as a **Databricks App**.
It exposes a few demo tools (user identity, savings account details, savings forecast) and
shows how to consume them from notebooks, agents and IDE clients.

## Repository layout

```
.
├── server/
│   ├── app.py          # FastAPI + FastMCP app (Streamable HTTP at /mcp, /health)
│   ├── main.py         # Entry point (`custom-server`), runs uvicorn
│   ├── tools.py        # MCP tool definitions and demo account data
│   └── utils.py        # Per-user WorkspaceClient (on-behalf-of auth)
├── scripts/
│   ├── list_tools.py       # Lists the tools of an MCP server (default: local)
│   └── mcp_stdio_proxy.py  # stdio <-> HTTP bridge for IDE clients (OAuth handled via Databricks SDK)
├── notebooks/
│   ├── mcp_client_basics.ipynb          # Talking to the MCP server directly
│   ├── hand_wired_agent_with_mcp.ipynb  # Hand-written agent loop using the MCP tools
│   └── openai_agent_with_mcp.ipynb      # OpenAI Agents SDK + MCP server
├── app.yaml            # Databricks App runtime config
├── databricks.yml      # Databricks Asset Bundle (app resource, dev/prod targets)
├── Makefile
└── pyproject.toml
```

## Tools

| Tool | Arguments | Description |
| --- | --- | --- |
| `health` | – | Server health check |
| `get_current_user` | – | Display name, user name and status of the calling Databricks user |
| `get_account_details` | – | Demo savings account (id, currency, balance) of the calling user |
| `forecast_savings` | `monthly_savings`, `years`, `annual_interest_rate=0.05` | Compound-interest forecast starting from the user's balance |

Demo accounts are keyed by Databricks user name in `ACCOUNTS` in [server/tools.py](server/tools.py) — add your own user there.

## Prerequisites

- [uv](https://docs.astral.sh/uv/)
- [Databricks CLI](https://docs.databricks.com/dev-tools/cli/) authenticated against your workspace
  (`databricks auth login --profile <profile>`)
- Node.js (only for the MCP Inspector)

## Local development

```bash
make run                  # install deps and start the server on http://localhost:8000
make list-tools           # in a second terminal: list tools of the local server
make inspector            # optional: open the MCP Inspector UI
```

Locally, tools authenticate with your Databricks CLI profile (`PROFILE`, default `default`,
exported as `DATABRICKS_CONFIG_PROFILE`).

Makefile variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `MCP_URL` | `http://localhost:8000/mcp` | Endpoint used by `list-tools` |
| `PROFILE` | `default` | Databricks CLI profile |
| `TARGET` | `dev` | Bundle target for `deploy` |

Example: `make list-tools MCP_URL=http://localhost:9000/mcp`

## Authentication

When deployed as a Databricks App, the user's token is forwarded in the
`x-forwarded-access-token` header and tools run **on behalf of the calling user**
(see [server/utils.py](server/utils.py)). Locally, the default Databricks SDK auth chain
(CLI profile) is used.

## Deploy to Databricks Apps

```bash
make deploy PROFILE=<profile> TARGET=dev
```

This logs in, deploys the bundle defined in [databricks.yml](databricks.yml) and starts the app.
The app reads package index URLs from the `databricks-package-management` secret scope
(`pip-index-url`, `pip-extra-index-urls`) — adjust or remove these resources in
`databricks.yml` / `app.yaml` if your workspace can reach PyPI directly.

The MCP endpoint is then available at `https://<app-host>/mcp`.

## Connecting clients

**VS Code / other stdio clients** — Databricks Apps require short-lived Databricks OAuth tokens,
so use the stdio proxy, which refreshes tokens via the Databricks SDK. Example `.vscode/mcp.json`:

```json
{
  "servers": {
    "databricks-mcp": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "run", "--project", "/path/to/databricks-mcp-template",
        "python", "scripts/mcp_stdio_proxy.py",
        "--url", "https://<app-host>/mcp",
        "--host", "https://<workspace-host>"
      ]
    }
  }
}
```

Run `databricks auth login --host https://<workspace-host>` once beforehand.

**Notebooks** — see [notebooks/](notebooks/) for direct client usage and agent examples
(hand-wired loop and OpenAI Agents SDK).

**Databricks Assistant / Genie** — the server runs in stateless HTTP mode and allows CORS
from Databricks domains, so it can be registered directly as a custom MCP server.
