> ⚠️ **Consolidated into [shesh-core](https://github.com/gaganjainse/shesh-core)** — this module now lives in the shesh-core monorepo (same package name, same console script). Archived 2026-08-13.

# 📦 shesh-mcp-bundle

Curated third-party MCP servers — **filesystem**, **fetch**, **git** — run as
subprocesses and proxied through the shesh-audit Guard so every tool call is
policy-checked and logged. Upstream servers are not re-implemented.

- License: GPL-3.0
- Layer: Soma
- Part of: [Shesh ecosystem](https://github.com/gaganjainse/shesh-ecosystem)

Servers are opt-in and skipped if their launcher (`npx`/`uvx`) is missing.

## Develop
```bash
uv run pytest -q
uv run ruff check .
uv run shesh-mcp-bundle-mcp
```

## Security

Security posture and vulnerability reporting: [canonical ecosystem security
policy](https://github.com/gaganjainse/shesh-ecosystem/blob/main/SECURITY.md).
