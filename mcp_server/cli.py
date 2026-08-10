import argparse
import os
import signal
import subprocess
import time

from .server import run_server


def free_port(port: int) -> None:
    """Kill a leftover mcp_server still holding the port, then return.

    A server suspended with Ctrl+Z (instead of stopped with Ctrl+C) keeps the
    port bound and the next start fails with "address already in use". Only
    processes whose command line contains "mcp_server" are killed, so an
    unrelated app on the same port is left alone (you'll get the normal bind
    error instead).
    """
    try:
        lsof = subprocess.run(
            ["lsof", "-ti", f"tcp:{port}"], capture_output=True, text=True
        )
    except FileNotFoundError:  # no lsof on this platform; let bind errors surface
        return
    freed = False
    for pid in lsof.stdout.split():
        ps = subprocess.run(
            ["ps", "-p", pid, "-o", "command="], capture_output=True, text=True
        )
        if "mcp_server" in ps.stdout:
            # SIGKILL: a Ctrl+Z-suspended process would never handle SIGTERM.
            os.kill(int(pid), signal.SIGKILL)
            print(f"Freed port {port}: killed leftover mcp_server (pid {pid}).",
                  flush=True)
            freed = True
    if freed:
        time.sleep(0.5)  # give the kernel a moment to release the socket


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
    if args.transport == "streamable-http":
        free_port(args.port)
    run_server(
        transport=args.transport,
        host=args.host,
        port=args.port,
    )
    return 0
