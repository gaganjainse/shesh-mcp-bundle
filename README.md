# shesh-mcp-bundle

> **Superseded by [shesh-core](https://github.com/gaganjainse/shesh-core).**
> This repository is a tombstone: its history is preserved, its source is not.

## What happened

[ADR-0019](https://github.com/gaganjainse/shesh-docs/blob/main/src/governance/adr/0019-shesh-core-monorepo.md)
consolidated the single-module services into one repository. A module of a few
hundred lines is not a service: each one carried its own build configuration,
pipeline, and security policy, and those drifted apart from each other.

The code now lives in `shesh-core` as the `shesh_mcp_bundle` package, with
the same import path and the same console script.

## Why the source was removed

Two copies of the same module drift. Keeping the code here meant a reader could
find it, edit it, and have the change silently ignored by everything that
actually runs.

The history remains in this repository's git log. Nothing was lost.

## Installing

```bash
pipx install git+https://github.com/gaganjainse/shesh-core.git
```

Console script names are unchanged, so existing client configuration keeps
working.

## Licence

GPL-3.0-or-later.
