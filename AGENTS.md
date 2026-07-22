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

zget downloads videos from social media platforms (YouTube, Instagram, TikTok, C-SPAN, etc.) and stores them locally with full metadata. It's the **only capture front-end** for librarian and Chimera A/V (never call yt-dlp directly). Integrates with media servers like Plex.

**Cross-project contract:** see `docs/INTEGRATION.md`.

## Key Files

| File | Purpose |
|------|---------|
| `src/zget/core.py` | yt-dlp wrapper, download / extract_info |
| `src/zget/platforms/cspan.py` | C-SPAN `/program/` → HLS resolve + Referer |
| `src/zget/library/paths.py` | Path health, ZGET_HOME migration rewrite |
| `src/zget/library/ingest.py` | Video ingest pipeline |
| `src/zget/cli.py` | CLI (`download`, `info`, `list-channel`, `doctor`, `paths`) |
| `src/zget/config.py` | Paths, `zget_home`, platform detection |
| `src/zget/types.py` | yt-dlp type aliases (`YtdlpInfo`, `ProgressDict`) |
| `src/zget/server/app.py` | FastAPI backend, settings API |
| `src/zget/server/static/` | Web Components UI (no build step) |
| `src/zget/db/async_store.py` | Async SQLite (server) |
| `src/zget/db/store.py` | Sync SQLite (CLI) |
| `src/zget/mcp/server.py` | MCP server for agent integration |
| `docs/INTEGRATION.md` | Librarian / Chimera / agent integration |

## Running the Project

**Zero-terminal (recommended for users):**

- macOS: Double-click `zget-start.command`

**Terminal:**

```bash
make bootstrap    # First-time setup
make serve        # Start web server on port 9989
uv run zget <url> # CLI download
uv run zget info <url>
uv run zget --doctor
uv run zget paths check
```

The `--open` flag auto-launches browser: `uv run zget-server --open`

## Library path rules (critical)

- Resolve home: `ZGET_HOME` → `~/.config/zget/config.json` `zget_home` → fallback `~/Downloads/zget`
- **Do not hardcode** `~/Downloads/zget` as the live library in agent instructions for this machine
- After moving home: `uv run zget paths rewrite` (or `--doctor --fix`) before purging orphans
- `--doctor --fix` only rewrites relocatable paths; **`--purge-orphans`** is required to delete missing rows
- Offline `/Volumes/...` paths are **not** orphans — remount first

## C-SPAN

- `c-span.org/video/?…` — normal yt-dlp  
- `c-span.org/program/.../{id}` — supported via public HLS + Referer (`platforms/cspan.py`)

## MCP Integration

zget exposes tools via `/src/zget/mcp/server.py`. Use `zget_get_local_path` to get file paths for handoff to other tools (e.g., transcription, analysis).

## Design Notes

- **Framework-Free Frontend**: The web UI uses native Web Components, no build step
- **H.264 Standard**: All videos are transcoded to H.264/AAC for compatibility
- **Metadata First**: Every download preserves title, uploader, date, description
- **Public repo hygiene**: no operator volume names, private corpus paths, or real Tailscale IPs in commits
