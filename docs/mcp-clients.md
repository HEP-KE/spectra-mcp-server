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

## Hosting beyond localhost

**Security first**: these tutorial servers have **no authentication**, and
their tools write files to any `output_dir` path — anyone holding the URL
can run compute and write files on the host machine. Expose them through
unguessable temporary URLs for demos, or put real auth in front (FastMCP
supports OAuth providers) before hosting anything persistent. Never leave a
public tunnel to your laptop running unattended.

### Quick tunnel — free, no account, verified working

```bash
brew install cloudflared
MCP_PUBLIC=1 python -m mcp_server --transport streamable-http --port 8000
cloudflared tunnel --url http://127.0.0.1:8000
```

`cloudflared` prints a random `https://<name>.trycloudflare.com` URL; remote
clients connect to `https://<name>.trycloudflare.com/mcp`. Two things to
know:

- `MCP_PUBLIC=1` is required: by default the MCP transport rejects requests
  whose `Host` header is not localhost (DNS-rebinding protection, HTTP 421).
  The env var disables that check for tunnel/cloud serving.
- The URL is random on every run and dies with the process — demo-grade by
  design, which is exactly the safety property you want here.

Remote configs, once you have the URL:

```bash
claude mcp add --transport http spectra https://<name>.trycloudflare.com/mcp
```

Cursor (`mcp.json`): `{"mcpServers": {"spectra": {"url": "https://<name>.trycloudflare.com/mcp"}}}`.
Claude desktop app: Settings → Connectors → Add custom connector → paste the
URL. Codex (stdio-only): bridge with
`command = "npx"`, `args = ["-y", "mcp-remote", "https://<name>.trycloudflare.com/mcp"]`.

### Persistent hosting (free tiers)

| option | cost | fits this server? |
|---|---|---|
| Hugging Face Spaces (Docker) | free, sleeps when idle | good — arbitrary Python + our data files; public URL |
| Google Cloud Run | free tier, scales to zero | good — container with the science stack; needs a credit card |
| Cloudflare Workers | free | poor fit — no CPython C extensions (classy/numpy) |
| Render free web service | free, sleeps + slow cold starts | workable for the gaia server; classy build is heavy |
| NERSC Spin / lab k8s | free for allocation holders | the real answer for this audience: persistent science services next to the data |

For any of these: build a small Docker image that `pip install`s the repo
and runs `MCP_PUBLIC=1 python -m mcp_server --transport streamable-http
--host 0.0.0.0 --port $PORT` — nothing else changes.
