import argparse

from .server import run_server


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m mcp_server",
        description="Run the MCP server wrapper.",
    )
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP transport. Use stdio for subprocess agents or streamable-http for a URL endpoint.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for streamable-http transport.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for streamable-http transport.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    run_server(
        transport=args.transport,
        host=args.host,
        port=args.port,
    )
    return 0
