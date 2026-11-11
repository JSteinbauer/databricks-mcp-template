import argparse
import os

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description="Start the MCP server")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("DATABRICKS_APP_PORT", 8000)),
        help="Port to run the server on (default: $DATABRICKS_APP_PORT or 8000)",
    )
    args = parser.parse_args()

    uvicorn.run("server.app:combined_app", host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
