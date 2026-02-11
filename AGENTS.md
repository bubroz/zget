<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:

- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:

- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# AI Assistant Instructions: zget

These instructions are for AI assistants working in this project.

## What zget Does

zget downloads videos from social media platforms (YouTube, Instagram, TikTok, etc.) and stores them locally with full metadata. It's designed for personal archival and integrates with media servers like Plex.

## Key Files

| File | Purpose |
|------|---------|
| `src/zget/core.py` | yt-dlp wrapper, download logic |
| `src/zget/cli.py` | Main CLI entry point |
| `src/zget/config.py` | All configuration and paths |
| `src/zget/types.py` | yt-dlp type aliases (`YtdlpInfo`, `ProgressDict`) |
| `src/zget/server/app.py` | FastAPI backend, settings API |
| `src/zget/library/ingest.py` | Video ingest pipeline |
| `src/zget/db/async_store.py` | Async SQLite operations (used by server) |
| `src/zget/db/store.py` | Sync SQLite operations (used by CLI) |
| `src/zget/mcp/server.py` | MCP server for agent integration |

## Running the Project

**Zero-terminal (recommended for users):**

- macOS: Double-click `zget-start.command`

**Terminal:**

```bash
make bootstrap    # First-time setup
make serve        # Start web server on port 9989
uv run zget <url> # CLI download
```

The `--open` flag auto-launches browser: `uv run zget-server --open`

## MCP Integration

zget exposes tools via `/src/zget/mcp/server.py`. Use `zget_get_local_path` to get file paths for handoff to other tools (e.g., transcription, analysis).

## Design Notes

- **Framework-Free Frontend**: The web UI uses native Web Components, no build step
- **H.264 Standard**: All videos are transcoded to H.264/AAC for compatibility
- **Metadata First**: Every download preserves title, uploader, date, description
