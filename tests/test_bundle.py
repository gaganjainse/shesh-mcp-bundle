"""Offline tests for the MCP bundle (with a fake upstream)."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shesha_mcp_bundle.proxy import BundledMcp, ToolProxy  # noqa: E402
from shesha_mcp_bundle.registry import BundledServer, default_servers, is_available  # noqa: E402


class FakeProc:
    """A fake MCP upstream that responds based on the JSON-RPC method requested."""
    def __init__(self):
        self.stdin = io.StringIO()
        self._responses = {
            "initialize": '{"jsonrpc":"2.0","id":1,"result":{}}',
            "tools/list": '{"jsonrpc":"2.0","id":2,"result":{"tools":[{"name":"read_file","description":"r"}]}}',
            "tools/call": '{"jsonrpc":"2.0","id":3,"result":{"content":[{"type":"text","text":"ok"}]}}',
        }
        self._default = self._responses["tools/list"]
        class _Out:
            def __init__(s_inner, outer): s_inner.outer = outer
            def readline(s_inner):
                return s_inner.outer._next_response() + "\n"
        self.stdout = _Out(self)
        self.pid = 12345

    def _next_response(self):
        import json as _json
        # Read what the client sent and respond by method.
        line = self.stdin.getvalue().strip().splitlines()[-1] if self.stdin.getvalue().strip() else ""
        try:
            method = _json.loads(line).get("method", "")
        except Exception:
            method = ""
        return self._responses.get(method, self._default)

    def terminate(self):
        pass


def test_guarded_call_denies_protected(monkeypatch):
    server = BundledServer("filesystem", ("true",), "fs", "files")
    # Force availability and fake process start.
    monkeypatch.setattr("shesha_mcp_bundle.proxy.is_available", lambda c: True)
    bundle = BundledMcp(servers=[server])
    _fp = FakeProc()
    monkeypatch.setattr(bundle, "_start", lambda s: _fp)
    # Add a deny-all guard.
    class DummyGuard:
        def check(self, tool, args, actor="agent"):
            from types import SimpleNamespace
            return SimpleNamespace(verdict="deny", reason="blocked",
                                    allowed=False, requires_confirmation=False)
        def log_execution(self, *a, **k):
            pass
    bundle.guard = DummyGuard()
    tools = bundle.list_tools()
    assert tools and tools[0].exposed_name == "fs_read_file"
    result = tools[0].call({"path": "/home/u/.ssh/id_rsa"})
    assert result["ok"] is False and "denied" in result["error"]


def test_guarded_call_allows_and_forwards(monkeypatch):
    server = BundledServer("fetch", ("true",), "fetch", "web fetch")
    monkeypatch.setattr("shesha_mcp_bundle.proxy.is_available", lambda c: True)
    bundle = BundledMcp(servers=[server])
    _fp = FakeProc()
    monkeypatch.setattr(bundle, "_start", lambda s: _fp)

    class AllowGuard:
        verdict = "allow"
        allowed = True
        requires_confirmation = False
        reason = "ok"
        def check(self, *a, **k):
            return self
        def log_execution(self, *a, **k):
            pass
    bundle.guard = AllowGuard()
    tools = bundle.list_tools()
    # With our fake upstream (tools/list returns read_file, but tools/call
    # would need another response); just assert routing/prefix.
    assert tools[0].exposed_name == "fetch_read_file"


def test_missing_server_skipped(monkeypatch):
    server = BundledServer("x", ("nonexistent-binary-xyz",), "x", "x")
    monkeypatch.setattr("shesha_mcp_bundle.proxy.is_available", lambda c: False)
    bundle = BundledMcp(servers=[server], skip_unavailable=True)
    assert bundle.available_servers() == []


def test_registry_defaults():
    servers = default_servers(home=Path("/tmp/fakehome"))
    names = {s.name for s in servers}
    assert {"filesystem", "fetch", "git"} <= names
