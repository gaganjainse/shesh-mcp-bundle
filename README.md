# 📦 shesha-mcp-bundle

Curated third-party MCP servers — **filesystem**, **fetch**, **git** — run as
subprocesses and proxied through the shesha-audit Guard so every tool call is
policy-checked and logged. Upstream servers are not re-implemented.

- License: GPL-3.0
- Layer: Soma
- Part of: [Shesha ecosystem](https://github.com/gaganjainse/shesha-ecosystem)

Servers are opt-in and skipped if their launcher (`npx`/`uvx`) is missing.

## Develop
```bash
uv run pytest -q
uv run ruff check .
uv run shesha-mcp-bundle-mcp
```
