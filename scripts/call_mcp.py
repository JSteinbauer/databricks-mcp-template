"""Call the mcp-server-template server with an MCP client.

Local:     uv run python scripts/call_mcp.py
Deployed:  uv run python scripts/call_mcp.py --url https://<app-url>/mcp
"""

import argparse
import asyncio
import json

from databricks.sdk import WorkspaceClient
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

LOCAL_URL = "http://localhost:8000/mcp"


async def run(url: str, monthly_savings: float, years: int, rate: float) -> None:
    # Databricks Apps only accept OAuth tokens; reuse the local Databricks CLI/SDK auth.
    headers = {} if url.startswith("http://localhost") else WorkspaceClient().config.authenticate()

    async with Client(StreamableHttpTransport(url, headers=headers)) as client:
        tools = await client.list_tools()
        print("Tools:", [t.name for t in tools])

        for name, args in [
            ("get_account_details", {}),
            ("forecast_savings", {"monthly_savings": monthly_savings, "years": years, "annual_interest_rate": rate}),
        ]:
            result = await client.call_tool(name, args, raise_on_error=False)
            print(f"\n{name}({args}):")
            if result.is_error:
                print("ERROR:", result.content[0].text)
            else:
                print(json.dumps(result.structured_content, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", default=LOCAL_URL, help=f"MCP endpoint (default: {LOCAL_URL})")
    parser.add_argument("--monthly-savings", type=float, default=200.0)
    parser.add_argument("--years", type=int, default=10)
    parser.add_argument("--rate", type=float, default=0.05, help="annual interest rate, e.g. 0.05")
    args = parser.parse_args()
    asyncio.run(run(args.url, args.monthly_savings, args.years, args.rate))


if __name__ == "__main__":
    main()
