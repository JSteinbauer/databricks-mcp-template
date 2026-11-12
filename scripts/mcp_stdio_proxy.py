#!/usr/bin/env python3
"""
stdio <-> Streamable-HTTP bridge for an MCP server hosted on Databricks Apps.

Databricks Apps only accept Databricks OAuth (U2M) tokens, which expire hourly.
This bridge obtains/refreshes the token through the Databricks SDK (CLI token
cache or any other configured auth) and forwards each JSON-RPC message from
stdin to the app's /mcp endpoint, writing responses back to stdout.
If the server drops the MCP session (e.g. app restart), the bridge
transparently re-initializes it and retries the request.

Usage (from .vscode/mcp.json):
    uv run --project <repo> python scripts/mcp_stdio_proxy.py \
        --url https://<app-host>/mcp --host https://<workspace-host>

Prerequisite: `databricks auth login --host https://<workspace-host>` once.
"""

import argparse
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

import requests
from databricks.sdk.core import Config

_stdout_lock = threading.Lock()


def _emit(payload: str) -> None:
    with _stdout_lock:
        sys.stdout.write(payload.rstrip("\n") + "\n")
        sys.stdout.flush()


def _log(msg: str) -> None:
    sys.stderr.write(f"[mcp-proxy] {msg}\n")
    sys.stderr.flush()


def _parse_sse(body: str):
    """Yield the `data:` payload of each SSE event."""
    data_lines: list[str] = []
    for line in body.splitlines() + [""]:
        if line.startswith("data:"):
            data_lines.append(line[5:].lstrip())
        elif line == "" and data_lines:
            yield "\n".join(data_lines)
            data_lines = []


class Bridge:
    def __init__(self, url: str, cfg: Config):
        self.url = url
        self.cfg = cfg
        self.session = requests.Session()
        self.session_id: str | None = None
        self._init_msg: dict | None = None
        self._reinit_lock = threading.Lock()

    def _headers(self) -> dict[str, str]:
        headers = dict(self.cfg.authenticate())  # SDK refreshes the OAuth token as needed
        headers["Content-Type"] = "application/json"
        headers["Accept"] = "application/json, text/event-stream"
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        return headers

    def _post(self, body: str) -> requests.Response:
        resp = self.session.post(self.url, data=body.encode("utf-8"), headers=self._headers(), timeout=300)
        if sid := resp.headers.get("mcp-session-id"):
            self.session_id = sid
        return resp

    def _reinitialize(self, stale_session_id: str | None) -> bool:
        """Open a new MCP session by replaying the client's original initialize handshake."""
        with self._reinit_lock:
            if self.session_id != stale_session_id:
                return True  # another thread already re-initialized
            if self._init_msg is None:
                return False
            _log("MCP session expired, re-initializing")
            self.session_id = None
            init = dict(self._init_msg, id="mcp-proxy-reinit")
            try:
                resp = self._post(json.dumps(init))
                if resp.status_code >= 400:
                    _log(f"re-initialize failed: HTTP {resp.status_code}: {resp.text[:500]}")
                    return False
                self._post(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}))
            except requests.RequestException as exc:
                _log(f"re-initialize failed: {exc}")
                return False
            return True

    def handle(self, line: str) -> None:
        line = line.strip()
        if not line:
            return
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            _log(f"skipping non-JSON input: {line[:80]!r}")
            return

        if isinstance(msg, dict) and msg.get("method") == "initialize":
            self._init_msg = msg
            self.session_id = None

        try:
            sent_with = self.session_id
            resp = self._post(line)
            # 404 on a request carrying a session id means the server forgot the session.
            if resp.status_code == 404 and sent_with and self._reinitialize(sent_with):
                resp = self._post(line)
        except requests.RequestException as exc:
            self._error(msg, f"HTTP request failed: {exc}")
            return

        if resp.status_code == 202 or not resp.content:
            return  # notification / response accepted, nothing to relay
        if resp.status_code >= 400:
            self._error(msg, f"HTTP {resp.status_code}: {resp.text[:500]}")
            return

        ctype = resp.headers.get("content-type", "")
        if ctype.startswith("text/event-stream"):
            for data in _parse_sse(resp.text):
                _emit(data)
        else:
            _emit(resp.text)

    @staticmethod
    def _error(msg: dict, text: str) -> None:
        _log(text)
        if isinstance(msg, dict) and "id" in msg:  # only requests get a JSON-RPC error back
            _emit(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "error": {"code": -32000, "message": text}}))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--url", required=True, help="MCP endpoint of the Databricks App, e.g. https://<app>/mcp")
    parser.add_argument("--host", default=os.getenv("DATABRICKS_HOST"), help="Workspace URL used to mint the OAuth token")
    parser.add_argument("--profile", default=os.getenv("DATABRICKS_CONFIG_PROFILE"), help="Databricks CLI profile")
    args = parser.parse_args()

    cfg_kwargs: dict[str, str] = {}
    if args.profile:
        cfg_kwargs["profile"] = args.profile
    elif args.host:
        cfg_kwargs["host"] = args.host
    cfg = Config(**cfg_kwargs)
    _log(f"forwarding stdio -> {args.url} (auth_type={cfg.auth_type}, host={cfg.host})")

    bridge = Bridge(args.url, cfg)
    with ThreadPoolExecutor(max_workers=8) as pool:
        for line in iter(sys.stdin.readline, ""):
            pool.submit(bridge.handle, line)


if __name__ == "__main__":
    main()
