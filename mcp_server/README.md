# mcp_server — drop-in MCP wrapper

Copy this directory into the root of any science repo to publish its functions
as MCP tools.

1. In your repo's `pyproject.toml`, add:

   ```toml
   [tool.mcp-server]
   tool_modules = ["your_science_package"]
   ```

2. In that package's `__init__.py`, list the public tool functions in
   `__all__`. Only those names are exposed; helpers stay private.

3. Make sure `mcp[cli]>=1.27,<2` is a dependency.

Run with `python -m mcp_server --transport stdio|streamable-http [--host --port]`.

The wrapper walks up from its own location to find `pyproject.toml`, imports
the configured modules, and registers each `__all__` entry with FastMCP. Type
hints, Pydantic constraints, and docstrings become the tool schema.
