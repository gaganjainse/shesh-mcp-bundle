"""Subprocess proxy for an upstream MCP server, with Guard enforcement.

This is a minimal MCP stdio client: it spawns the upstream server, performs
the initialize handshake, lists tools, and forwards tool calls — but checks
each call against the Guard before forwarding and logs the result after.

It is intentionally synchronous and line/buffer based; it covers the common
stdio servers we bundle and is fully testable with a fake upstream process.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from typing import Any

from .registry import BundledServer, is_available


@dataclass
class ToolProxy:
    bundle: BundledMcp
    server: BundledServer
    upstream_name: str

    @property
    def exposed_name(self) -> str:
        return f"{self.server.prefix}_{self.upstream_name}"

    def call(self, arguments: dict) -> dict:
        # Policy gate (the Guard is injected from the bundle).
        if self.bundle.guard is not None:
            decision = self.bundle.guard.check(
                self.exposed_name, arguments, actor=f"bundle:{self.server.name}")
            if decision.verdict == "deny":
                return {"ok": False, "error": f"denied: {decision.reason}"}
        try:
            raw = self.bundle._call_upstream(self.server, "tools/call", {
                "name": self.upstream_name, "arguments": arguments,
            })
            result = raw.get("result", raw) if isinstance(raw, dict) else raw
            ok = "error" not in result if isinstance(result, dict) else True
            if self.bundle.guard is not None:
                self.bundle.guard.log_execution(
                    self.exposed_name, ok, actor=f"bundle:{self.server.name}",
                    args=arguments, result=str(result)[:200])
            return result
        except Exception as e:  # noqa: BLE001
            if self.bundle.guard is not None:
                self.bundle.guard.log_execution(
                    self.exposed_name, False, actor=f"bundle:{self.server.name}",
                    result=str(e)[:200])
            return {"ok": False, "error": str(e)}


@dataclass
class BundledMcp:
    servers: list[BundledServer]
    guard: Any = None
    skip_unavailable: bool = True
    _procs: dict[str, subprocess.Popen] = field(default_factory=dict)
    _handshaken: set[str] = field(default_factory=set)
    _id: int = 0

    def available_servers(self) -> list[BundledServer]:
        out = []
        for s in self.servers:
            if is_available(s.command[0]):
                out.append(s)
            elif s.required and not self.skip_unavailable:
                raise RuntimeError(f"required server {s.name} command not found")
        return out

    def _start(self, server: BundledServer) -> subprocess.Popen:
        if server.name in self._procs:
            return self._procs[server.name]
        proc = subprocess.Popen(
            list(server.command),
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, bufsize=1,
        )
        self._procs[server.name] = proc
        if server.name not in self._handshaken:
            self._handshake(proc)
            self._handshaken.add(server.name)
        return proc

    def _handshake(self, proc: subprocess.Popen) -> None:
        self._write(proc, {
            "jsonrpc": "2.0", "id": self._next(), "method": "initialize",
            "params": {"protocolVersion": "2024-11-05",
                       "capabilities": {}, "clientInfo": {"name": "shesh-mcp-bundle"}},
        })
        self._read(proc)  # initialize result
        self._notify(proc, "notifications/initialized")

    def list_tools(self) -> list[ToolProxy]:
        tools: list[ToolProxy] = []
        for s in self.available_servers():
            try:
                self._start(s)
                resp = self._call_upstream(s, "tools/list", {})
                for t in resp.get("result", resp).get("tools", []):
                    tools.append(ToolProxy(self, s, t["name"]))
            except Exception:
                if s.required:
                    raise
        return tools

    def _call_upstream(self, server: BundledServer, method: str, params: dict) -> dict:
        proc = self._start(server)
        self._write(proc, {"jsonrpc": "2.0", "id": self._next(),
                            "method": method, "params": params})
        return self._read(proc)

    def _next(self) -> int:
        self._id += 1
        return self._id

    @staticmethod
    def _write(proc: subprocess.Popen, msg: dict) -> None:
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()

    @staticmethod
    def _notify(proc: subprocess.Popen, method: str) -> None:
        proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method}) + "\n")
        proc.stdin.flush()

    @staticmethod
    def _read(proc: subprocess.Popen) -> dict:
        line = proc.stdout.readline()
        if not line:
            raise RuntimeError("upstream MCP server closed connection")
        return json.loads(line)

    def shutdown(self) -> None:
        for proc in self._procs.values():
            proc.terminate()
        self._procs.clear()
