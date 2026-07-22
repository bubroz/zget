# zget

Agentic local media capture. Download and archive media from YouTube, Instagram, TikTok, Reddit, X, Twitch, C-SPAN, and other sites yt-dlp supports. Library with metadata, dedupe, path health, CLI, and MCP for agents and pipelines.

There is **no web UI**. Use the CLI or MCP.

## Requirements

- macOS or Linux
- Python 3.10+
- [uv](https://docs.astral.sh/uv/)
- ffmpeg

## Install

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
brew install ffmpeg   # macOS

git clone https://github.com/bubroz/zget.git
cd zget
uv sync
```

## Library path

Media and `library.db` live under **ZGET_HOME**:

1. `ZGET_HOME` env
2. `~/.config/zget/config.json` key `zget_home`
3. Default: `~/Downloads/zget`

```bash
uv run zget config show
uv run zget config set zget_home /path/to/library
```

```text
$ZGET_HOME/
  library.db
  videos/<platform>/
  thumbnails/
  exports/
  logs/
```

## CLI

```bash
# download
uv run zget <url>
uv run zget <url> --quiet
uv run zget <url> --flat
uv run zget <url> -o /path/to/dir
uv run zget <url> --audio-only
uv run zget <url> --quality 720

# metadata only
uv run zget info <url>
uv run zget info <url> --json --compact
uv run zget --list-formats <url>
uv run zget list-channel <channel-or-playlist-url> --since 2020-01-01 --jsonl

# library
uv run zget --search "query"
uv run zget --stats
uv run zget --doctor
uv run zget --doctor --fix
uv run zget paths check
uv run zget paths rewrite --dry-run
uv run zget paths rewrite

# config
uv run zget config show
uv run zget config set flat true
```

### C-SPAN

- `c-span.org/video/?...` via yt-dlp
- `c-span.org/program/.../{id}` via public HLS + Referer (`src/zget/platforms/cspan.py`)

### Path health

| Class | Meaning |
|-------|---------|
| healthy | File exists under ZGET_HOME |
| relocatable | Stale path; file found after home or volume rename |
| off-home | File exists outside ZGET_HOME (pipeline `-o`) |
| offline volume | Unmounted `/Volumes/...` with no sibling match |
| orphan | File missing |

`--doctor --fix` rewrites relocatable paths only. Use `--purge-orphans` only when you intend to drop missing rows.

## Agents (MCP)

```bash
uv run zget-mcp
```

```json
{
  "mcpServers": {
    "zget": {
      "command": "uv",
      "args": ["run", "zget-mcp"],
      "cwd": "/path/to/zget",
      "env": { "PATH": "/opt/homebrew/bin:/usr/bin:/bin" }
    }
  }
}
```

| Tool | Role |
|------|------|
| `zget_download` | Download URL into the library |
| `zget_search` | Full-text search |
| `zget_get_video` | Metadata by id |
| `zget_get_local_path` | Filesystem path for other tools |
| `zget_extract_info` | Metadata without download |
| `zget_list_formats` | Formats |
| `zget_check_url` | Already archived? |
| `zget_get_recent` | Recent downloads |
| `zget_get_by_uploader` | By channel |

Full contract for other repos: [docs/INTEGRATION.md](docs/INTEGRATION.md).

## Platforms

Verified: YouTube, Instagram, X, TikTok, Reddit, Twitch, C-SPAN (including program pages). Many more via yt-dlp.

## Layout

```text
src/zget/
  core.py           # yt-dlp download / extract
  platforms/        # adapters (C-SPAN program HLS)
  library/          # ingest, paths, thumbnails
  cli.py            # CLI
  mcp/              # MCP (stdio)
  db/               # SQLite FTS5
  metadata/         # NFO sidecars
  ...
```

## Dev

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src
```

## License

MIT. Built on [yt-dlp](https://github.com/yt-dlp/yt-dlp).
