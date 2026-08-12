"""MCP server exposing the bundled third-party tools behind the Guard."""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .proxy import BundledMcp, ToolProxy
from .registry import default_servers

try:
    from shesh_audit.mcp_guard import GuardedMCP as _MCP
except ImportError:
    _MCP = FastMCP

mcp = _MCP("shesh-mcp-bundle")

_bundle = BundledMcp(servers=default_servers())


def _register_tools() -> None:
    """Discover bundled tools and register each as an MCP tool."""
    for proxy in _bundle.list_tools():
        _make_tool(proxy)


def _make_tool(proxy: ToolProxy):
    # Register with a stable name; docstring becomes the tool description.
    @mcp.tool(name=proxy.exposed_name)
    def _tool(**kwargs) -> dict:  # noqa: ANN003
        return proxy.call(kwargs)
    _tool.__doc__ = f"Bundled '{proxy.server.name}' tool: {proxy.upstream_name}"
    return _tool


# Register at import so the MCP server advertises them (lazily started).
_register_tools()


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
