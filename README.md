# spectra-mcp-server

**Part 1 of the client-server agent tutorial.** An MCP server that exposes
science tools — CLASS matter power spectra compared against eBOSS DR14
Lyman-α forest data — to any LLM agent.

Part 2, the multi-agent client that drives this server, lives in
[`multiagent-client-demo`](https://github.com/HEP-KE/multiagent-client-demo).
Setup instructions for both repos are in that repo's
[`prep.md`](https://github.com/HEP-KE/multiagent-client-demo/blob/main/prep.md).

## The one idea this repo teaches

> **The science code stays in usual Python. The MCP wrapper only publishes it.**

- `tools/` is an ordinary science package. It never imports MCP. The power-spectrum example lives in
  `tools/spectra_tools.py`. 
- `mcp_server/` is a ~70-line generic wrapper. It reads one line of config from
  `pyproject.toml`, imports the science package, and registers every function
  listed in its `__all__` as an MCP tool.

```toml
[tool.mcp-server]
tool_modules = ["tools"]
```

Your type hints, Pydantic `Field` constraints, and docstrings become the tool
schema agents see. To build your own server: drop your modules into `tools/`
(or point that one config line at your own package), list the public functions
in `__all__`, done.

## Layout

```
data/DR14_pm3d_19kbins.txt        eBOSS DR14 Ly-α P(k): 19 bins of (k, P, σ)
tools/
  cosmology.py                    CLASS parameter sets (Planck 2018) + run_class()
  spectra_tools.py                the 4 tool functions + ArtifactResult contract
  __init__.py                     __all__ — ONLY these names become tools
mcp_server/                       generic drop-in wrapper (FastMCP)
notebooks/01_manual_pipeline.ipynb  a walkthrough: science → tools → server
tests/test_tools.py               tools tested as plain Python, no MCP needed
```

### About the data file

`DR14_pm3d_19kbins.txt` is taken from
[marius311/mpk_compilation](https://github.com/marius311/mpk_compilation)
(Chabanier, Millea & Palanque-Delabrouille 2019,
[arXiv:1905.08103](https://arxiv.org/abs/1905.08103)): the **z = 0 linear**
matter power spectrum inferred from the eBOSS DR14 Ly-α forest. Mind the
file's mixed units — **k is in 1/Mpc while P(k), σ are in (Mpc/h)³** (the
source notebook plots `errorbar(k/h, Pk)`). `tools/spectra_tools.py` does the
`k/h` conversion once, on load; read the file any other way and the data
appears offset from theory by a factor ~2.

## Tools

| tool | what it does |
|---|---|
| `get_eboss_data()` | return the 19 observed (k, P(k), σ) bins |
| `list_cosmology_models()` | valid model names (`lcdm`, `nu_mass`, `wcdm`) + tunables |
| `compute_power_spectrum(model, output_dir, ...)` | run CLASS, write `pk_<model>.csv` |
| `plot_power_spectra(spectrum_files, output_dir, ...)` | two-panel figure: P(k) + data, ratio panel |

Two conventions worth copying into any science MCP server:

1. Every tool returns `{status, files, message, metadata}` (`ArtifactResult`).
2. Arrays move between tools **as file paths**, never through the agent's
   context window.

## Install

```bash
conda create -n spectra-tutorial python=3.12 -y
conda activate spectra-tutorial
pip install -e ".[dev]"       # classy compiles from source; see prep.md if it fails
pytest                        # 7 tests, no server or API key needed
```

## Run the server

**Streamable HTTP** — the server is a visible process with a URL:

```bash
python -m mcp_server --transport streamable-http --port 8000
```

Clients connect to `http://127.0.0.1:8000/mcp`. Stop the server with
**Ctrl+C** (Ctrl+Z only suspends it, leaving the port taken — if that
happens, just start the server again: it detects a leftover `mcp_server`
holding the port and clears it automatically).

To use this server from Claude Code, the Claude desktop app, Codex, Cursor,
or any other MCP client — or to run it **alongside** `gaia-mcp-server`
(ports 8000/8001) — see [`docs/mcp-clients.md`](docs/mcp-clients.md); a
checked-in `.mcp.json` already wires it into Claude Code.

## Try the hosted instance — no install needed

A live copy of this server (and its Gaia twin) is running for tutorial
sessions:

| server | MCP endpoint |
|---|---|
| spectra | `https://spectra.77-42-88-84.sslip.io/mcp` |
| gaia | `https://gaia.77-42-88-84.sslip.io/mcp` |

Connect from any MCP client, for example:

```bash
claude mcp add --transport http spectra https://spectra.77-42-88-84.sslip.io/mcp
```

(Claude desktop app: Settings → Connectors → Add custom connector → paste
the endpoint. Cursor: a `"url"` entry in `mcp.json`.)

Ask the agent to save files under `/srv/artifacts/<your-name>` — that is the
server's disk — then browse your figures at
<https://files.77-42-88-84.sslip.io/>. This is a small demo box: be gentle,
and expect it to be rebuilt or offline outside tutorial sessions.

## Start with the notebook

`notebooks/01_manual_pipeline.ipynb` builds everything up in order: the data,
the science by hand, the same science as tools, then the server. Committed
outputs let you read it without running anything.
