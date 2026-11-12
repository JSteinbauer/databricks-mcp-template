MCP_URL ?= http://localhost:8000/mcp
TARGET  ?= dev
PROFILE ?= default

export DATABRICKS_CONFIG_PROFILE := $(PROFILE)

.PHONY: install run client list-tools inspector deploy start

install:
	uv sync

run: install
	uv run custom-server

client:
	uv run python scripts/call_mcp.py --url $(MCP_URL)

list-tools:
	uv run python scripts/list_tools.py --url $(MCP_URL)

deploy:
	databricks auth login --profile $(PROFILE)
	databricks bundle deploy -t $(TARGET)
	databricks bundle run mcp_server_template -t $(TARGET)
