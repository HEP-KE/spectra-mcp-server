import importlib
from pathlib import Path
import tomllib
from typing import Literal

from mcp.server.fastmcp import FastMCP

Transport = Literal["stdio", "streamable-http"]


def pyproject_toml() -> Path:
    for directory in Path(__file__).resolve().parents:
        path = directory / "pyproject.toml"
        if path.exists():
            return path
    raise FileNotFoundError("Could not find pyproject.toml")


def configured_tool_module_names() -> list[str]:
    path = pyproject_toml()
    config = tomllib.loads(path.read_text(encoding="utf-8"))
    try:
        return list(config["tool"]["mcp-server"]["tool_modules"])
    except KeyError as exc:
        raise RuntimeError(
            f"{path} must contain a [tool.mcp-server] section with a "
            'tool_modules list, e.g.\n\n[tool.mcp-server]\ntool_modules = ["tools"]'
        ) from exc


def load_tool_modules():
    return [
        importlib.import_module(module_name)
        for module_name in configured_tool_module_names()
    ]


def create_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8000,
) -> FastMCP:
    mcp = FastMCP(
        "Spectra MCP Server",
        instructions=(
            "Cosmology tools: compute linear matter power spectra with CLASS and "
            "compare them to eBOSS DR14 Lyman-alpha data. Tools that write files "
            "accept an output_dir argument and return structured artifact metadata; "
            "pass file paths between tools, never raw arrays."
        ),
        host=host,
        port=port,
    )

    for tool_module in load_tool_modules():
        if not hasattr(tool_module, "__all__"):
            raise RuntimeError(
                f"Tool module '{tool_module.__name__}' must define __all__ "
                "listing the functions to expose as MCP tools."
            )
        for name in tool_module.__all__:
            mcp.tool()(getattr(tool_module, name))
    return mcp


def run_server(
    *,
    transport: Transport = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    mcp = create_server(host=host, port=port)
    mcp.run(transport=transport)
