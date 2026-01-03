# OpenSpec Agent Instructions

These instructions explain how AI assistants should use OpenSpec in this project, operating within the **Archivist/Vault/Portal** architectural framework.

## Project Overview

zget is a high-fidelity media archival system built for the Digital Intelligence Ecosystem with:

- **1,899 supported extractors** via yt-dlp orchestration.
- **The Vault**: SQLite-backed library with FTS5 search and H.264 standard enforcement.
- **The Portal**: Premium glassmorphism PWA for discovery and native iOS playback.

## When to Use OpenSpec

Use OpenSpec when:

- Adding new platform support or extractor features.
- Modifying the API (FastAPI routes in `app.py`).
- Adding new background repair or maintenance tasks.
- Major refactoring of core components (core, db, server).

## Directory Structure

```
src/zget/
├── server/         # The Portal (FastAPI & PWA)
├── mcp/            # MCP server for agentic handoffs
├── core.py         # The Archivist (Archival Engine)
├── db/             # The Vault (Persistence)
├── health.py       # Smokescreen Verification Engine
└── cli.py          # Unified entry point & status
```

## Key Components

| Component | Purpose |
|-----------|---------|
| `core.py` | yt-dlp wrapper and download orchestration (The Archivist) |
| `health.py` | Site health monitoring using smokescreen tests |
| `server/app.py` | FastAPI application and API routes |
| `db/store.py` | SQLite operations and FTS5 search (The Vault) |
| `server/static/` | PWA Frontend and manifest (The Portal) |

## Creating a Change Proposal

1. Create folder: `openspec/changes/add-<feature>/`
2. Add `proposal.md` with Why/What/Impact.
3. Add `tasks.md` with checklist.
4. Implement the change.
5. Archive when done.

## Quick Reference

```bash
# Validate specs and changes
npx openspec validate

# Start the full stack
uv run zget-server --port 8000 --host 0.0.0.0
```
