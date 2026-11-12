from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastmcp import FastMCP

from server.tools import register_tools

mcp_server = FastMCP(name="mcp-server-template")
register_tools(mcp_server)

# Stateless so clients without an mcp-session-id header (e.g. Databricks Assistant) work
mcp_app = mcp_server.http_app(path="/mcp", stateless_http=True)

app = FastAPI(
    title="mcp-server-template",
    description="MCP server exposing account details and savings forecasts",
    version="0.1.0",
    lifespan=mcp_app.lifespan,
)


@app.get("/", include_in_schema=False)
async def index() -> dict:
    return {"message": "mcp-server-template MCP server is running", "status": "healthy"}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# Served by uvicorn: server.app:combined_app
combined_app = FastAPI(
    title="mcp-server-template",
    routes=[*mcp_app.routes, *app.routes],
    lifespan=mcp_app.lifespan,
)

# Needed for cross-origin requests from Databricks domains (e.g. genie code)
combined_app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://[a-z0-9.-]+\.(azuredatabricks\.net|databricksapps\.com)",
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Mcp-Session-Id"],
)