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
| `src/zget/library/ingest.py` | Video ingest pipeline |
| `src/zget/db/store.py` | SQLite database operations |
| `src/zget/mcp/server.py` | MCP server for agent integration |

## Running the Project

```bash
make bootstrap    # First-time setup
make serve        # Start web server on port 8000
uv run zget <url> # CLI download
```

## MCP Integration

zget exposes tools via `/src/zget/mcp/server.py`. Use `zget_get_local_path` to get file paths for handoff to other tools (e.g., transcription, analysis).

## Design Notes

- **Framework-Free Frontend**: The web UI uses native Web Components, no build step
- **H.264 Standard**: All videos are transcoded to H.264/AAC for compatibility
- **Metadata First**: Every download preserves title, uploader, date, description
