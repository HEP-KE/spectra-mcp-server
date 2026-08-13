# Using this server from any MCP client

The LangGraph client in
[`multiagent-client-demo`](https://github.com/HEP-KE/multiagent-client-demo)
is just *one* MCP client. The same server plugs into Claude Code, the Claude
desktop app, Codex, Cursor — anything that speaks MCP. That versatility is
the point of the protocol.

## The two facts every config needs

1. **stdio launch command**: `python -m mcp_server --transport stdio`, run so
   that this repo is importable — either the working directory is the repo
   root, or `PYTHONPATH` points at it.
2. **HTTP endpoint**: run `python -m mcp_server --transport streamable-http
   --port 8000` in a terminal; clients connect to
   `http://127.0.0.1:8000/mcp`.

`python` must be the tutorial environment's Python. GUI apps do not inherit
your shell, so configs below use the absolute interpreter path — find yours
with `conda activate spectra-tutorial && which python`.

## Claude Code

A project config (`.mcp.json`) is checked into this repo. Activate the env,
`cd` here, run `claude` — the `spectra` server is available (inspect with
`/mcp`). Or add it yourself:

```bash
claude mcp add spectra -- python -m mcp_server --transport stdio   # from this repo root
claude mcp add --transport http spectra http://127.0.0.1:8000/mcp  # server already running
```

## Claude desktop app

Settings → Developer → Edit Config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "spectra": {
      "command": "/ABS/PATH/TO/envs/spectra-tutorial/bin/python",
      "args": ["-m", "mcp_server", "--transport", "stdio"],
      "env": { "PYTHONPATH": "/ABS/PATH/TO/spectra-mcp-server" }
    }
  }
}
```

## Codex CLI

`~/.codex/config.toml`:

```toml
[mcp_servers.spectra]
command = "/ABS/PATH/TO/envs/spectra-tutorial/bin/python"
args = ["-m", "mcp_server", "--transport", "stdio"]
env = { PYTHONPATH = "/ABS/PATH/TO/spectra-mcp-server" }
```

## Cursor (untested)

`.cursor/mcp.json` in a project, or `~/.cursor/mcp.json` globally — same
JSON shape as the Claude desktop config above.

## Running both tutorial servers at once

[`gaia-mcp-server`](https://github.com/HEP-KE/gaia-mcp-server) coexists with
this one; give each its own port:

```bash
python -m mcp_server --transport streamable-http --port 8000
python -m mcp_server --transport streamable-http --port 8001
```

(first command from `spectra-mcp-server/`, second from `gaia-mcp-server/`).
Two caveats: use **distinct ports** — the automatic port-clearing on
startup kills any leftover `mcp_server` process holding the requested
port — and don't `pip install -e` both repos into one environment (they
export the same package names); the per-server `PYTHONPATH`/working
directory in the configs is what keeps them apart.

For stdio clients, just add both entries, each with its own `PYTHONPATH`:

```json
{
  "mcpServers": {
    "spectra": { "command": "/ABS/.../bin/python",
                 "args": ["-m", "mcp_server", "--transport", "stdio"],
                 "env": { "PYTHONPATH": "/ABS/PATH/TO/spectra-mcp-server" } },
    "gaia":    { "command": "/ABS/.../bin/python",
                 "args": ["-m", "mcp_server", "--transport", "stdio"],
                 "env": { "PYTHONPATH": "/ABS/PATH/TO/gaia-mcp-server" } }
  }
}
```

The tutorial's own client does the same thing in
`multiagent-client-demo/notebooks/05_multi_server.ipynb` — one agent, both
servers, tool names never clash.
