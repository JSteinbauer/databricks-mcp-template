MCP_URL ?= http://localhost:8000/mcp
TARGET  ?= dev
PROFILE ?= default

export DATABRICKS_CONFIG_PROFILE := $(PROFILE)

.PHONY: install run client inspector deploy start

install:
	uv sync

run: install
	uv run custom-server

client:
	uv run python scripts/call_mcp.py --url $(MCP_URL)

inspector:
	npx @modelcontextprotocol/inspector

deploy:
	databricks auth login --profile $(PROFILE)
	databricks bundle deploy -t $(TARGET)
	databricks bundle run mcp_server_template -t $(TARGET)
