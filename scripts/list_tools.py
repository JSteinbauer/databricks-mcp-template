#!/usr/bin/env python3
"""List the tools exposed by an MCP server (default: the local dev server).

Usage:
    uv run python scripts/list_tools.py [--url http://localhost:8000/mcp]
"""

import argparse
import asyncio

from fastmcp import Client


async def list_tools(url: str) -> None:
    async with Client(url) as client:
        tools = await client.list_tools()

    print(f"{len(tools)} tool(s) at {url}:\n")
    for tool in tools:
        params = ", ".join((tool.input_schema or {}).get("properties", {}))
        summary = (tool.description or "").strip().splitlines()[0] if tool.description else ""
        print(f"- {tool.name}({params})")
        if summary:
            print(f"    {summary}")


def main() -> None:
    parser = argparse.ArgumentParser(description="List tools of an MCP server")
    parser.add_argument("--url", default="http://localhost:8000/mcp", help="MCP endpoint URL")
    args = parser.parse_args()
    asyncio.run(list_tools(args.url))


if __name__ == "__main__":
    main()
