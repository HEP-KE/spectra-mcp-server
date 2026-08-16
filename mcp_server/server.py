import functools
import importlib
import inspect
import os
from pathlib import Path
import tomllib
from typing import Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

Transport = Literal["stdio", "streamable-http"]

# Hosted deployments set these (see docs/mcp-clients.md). Locally both are
# unset and nothing below changes.
#   MCP_OUTPUT_ROOT   e.g. /srv/artifacts — every output_dir an agent passes
#                     is remapped under this directory
#   MCP_ARTIFACT_URL  e.g. https://files.example.org — returned messages then
#                     include a browsable URL for each file written there
OUTPUT_ROOT = os.environ.get("MCP_OUTPUT_ROOT")
ARTIFACT_URL = (os.environ.get("MCP_ARTIFACT_URL") or "").rstrip("/")


def publish_outputs(func):
    """Confine a tool's output_dir to OUTPUT_ROOT and add URLs to its result.

    Agents on a remote server can't see its filesystem; this keeps every
    written file inside the one directory that is served over HTTP, no
    matter what path the agent asked for.
    """
    signature = inspect.signature(func)

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)
        requested = bound.arguments.get("output_dir")
        if requested is not None:
            root = Path(OUTPUT_ROOT)
            path = Path(str(requested))
            if not path.is_relative_to(root):
                # /tmp/pk -> <root>/tmp-pk : recognizable, but inside root
                safe = "-".join(part for part in path.parts if part != "/")
                bound.arguments["output_dir"] = str(root / (safe or "output"))
        result = func(*bound.args, **bound.kwargs)
        if ARTIFACT_URL and getattr(result, "files", None):
            urls = [f.replace(OUTPUT_ROOT, ARTIFACT_URL, 1)
                    for f in result.files if f.startswith(OUTPUT_ROOT)]
            if urls:
                result.message += " View: " + "  ".join(urls)
        return result

    return wrapper


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
    # By default the HTTP transport only accepts requests whose Host header is
    # localhost (DNS-rebinding protection) — remote clients get 421. Setting
    # MCP_PUBLIC=1 turns that check off for serving through a tunnel or a
    # cloud host. Only do this behind a private URL or with auth in front.
    transport_security = None
    if os.environ.get("MCP_PUBLIC"):
        transport_security = TransportSecuritySettings(
            enable_dns_rebinding_protection=False
        )

    instructions = (
        "Cosmology tools: compute linear matter power spectra with CLASS and "
        "compare them to eBOSS DR14 Lyman-alpha data. Tools that write files "
        "accept an output_dir argument and return structured artifact metadata; "
        "pass file paths between tools, never raw arrays."
    )
    if OUTPUT_ROOT:
        instructions += (
            f" This is a hosted server: all output files are stored under "
            f"{OUTPUT_ROOT} on the server (any other output_dir is remapped "
            "there), and results include browsable URLs — share those URLs "
            "with the user instead of trying to read or recreate the files."
        )

    mcp = FastMCP(
        "Spectra MCP Server",
        instructions=instructions,
        host=host,
        port=port,
        transport_security=transport_security,
    )

    for tool_module in load_tool_modules():
        if not hasattr(tool_module, "__all__"):
            raise RuntimeError(
                f"Tool module '{tool_module.__name__}' must define __all__ "
                "listing the functions to expose as MCP tools."
            )
        for name in tool_module.__all__:
            tool_function = getattr(tool_module, name)
            if OUTPUT_ROOT:
                tool_function = publish_outputs(tool_function)
            mcp.tool()(tool_function)
    return mcp


def run_server(
    *,
    transport: Transport = "stdio",
    host: str = "127.0.0.1",
    port: int = 8000,
) -> None:
    mcp = create_server(host=host, port=port)
    mcp.run(transport=transport)
