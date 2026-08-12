"""Offline tests for the MCP bundle (with a fake upstream)."""
from __future__ import annotations

import io
import json
import socket  # noqa: F401  (kept for future transport tests)
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shesh_mcp_bundle.proxy import BundledMcp  # noqa: E402
from shesh_mcp_bundle.registry import (  # noqa: E402
    BundledServer,
    default_servers,
)


class FakeProc:
    """A fake MCP upstream responding by JSON-RPC method."""

    def __init__(self):
        self.stdin = io.StringIO()
        self._by_method = {
            "initialize": '{"jsonrpc":"2.0","id":1,"result":{}}',
            "tools/list": (
                '{"jsonrpc":"2.0","id":2,"result":{"tools":['
                '{"name":"read_file","description":"r"}]}}'
            ),
            "tools/call": (
                '{"jsonrpc":"2.0","id":3,"result":'
                '{"content":[{"type":"text","text":"ok"}]}}'
            ),
        }

        class _Out:
            def __init__(self_inner, outer):
                self_inner.outer = outer

            def readline(self_inner):
                return self_inner.outer._next_response() + "\n"

        self.stdout = _Out(self)
        self.pid = 12345

    def _next_response(self) -> str:
        val = self.stdin.getvalue().strip()
        line = val.splitlines()[-1] if val else ""
        try:
            method = json.loads(line).get("method", "")
        except Exception:
            method = ""
        return self._by_method.get(method, self._by_method["tools/list"])

    def terminate(self):
        pass


def test_guarded_call_denies_protected(monkeypatch):
    server = BundledServer("filesystem", ("true",), "fs", "files")
    monkeypatch.setattr("shesh_mcp_bundle.proxy.is_available", lambda c: True)
    bundle = BundledMcp(servers=[server])
    fp = FakeProc()
    monkeypatch.setattr(bundle, "_start", lambda s: fp)

    class DummyGuard:
        verdict = "deny"
        allowed = False
        requires_confirmation = False
        reason = "blocked"

        def check(self, *a, **k):
            return self

        def log_execution(self, *a, **k):
            pass

    bundle.guard = DummyGuard()
    tools = bundle.list_tools()
    assert tools and tools[0].exposed_name == "fs_read_file"
    result = tools[0].call({"path": "/home/u/.ssh/id_rsa"})
    assert result["ok"] is False and "denied" in result["error"]


def test_guarded_call_allows_and_routes(monkeypatch):
    server = BundledServer("fetch", ("true",), "fetch", "web")
    monkeypatch.setattr("shesh_mcp_bundle.proxy.is_available", lambda c: True)
    bundle = BundledMcp(servers=[server])
    fp = FakeProc()
    monkeypatch.setattr(bundle, "_start", lambda s: fp)

    class Allow:
        verdict = "allow"
        allowed = True
        requires_confirmation = False
        reason = "ok"

        def check(self, *a, **k):
            return self

        def log_execution(self, *a, **k):
            pass

    bundle.guard = Allow()
    tools = bundle.list_tools()
    assert tools[0].exposed_name == "fetch_read_file"


def test_missing_server_skipped(monkeypatch):
    server = BundledServer("x", ("nonexistent-binary-xyz",), "x", "x")
    monkeypatch.setattr("shesh_mcp_bundle.proxy.is_available", lambda c: False)
    bundle = BundledMcp(servers=[server], skip_unavailable=True)
    assert bundle.available_servers() == []


def test_registry_defaults():
    servers = default_servers(home=Path("/tmp/fakehome"))
    names = {s.name for s in servers}
    assert {"filesystem", "fetch", "git"} <= names
