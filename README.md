# zget

Download and archive media from YouTube, Instagram, TikTok, Reddit, X, Twitch, C-SPAN, and other sites yt-dlp supports. Local library, metadata, CLI, optional web UI, MCP for agents.

This is a **capture tool** (the front end for projects like personal research pipelines). Prefer the CLI; the browser UI is optional.

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

## CLI (primary)

```bash
# download
uv run zget <url>
uv run zget <url> --quiet
uv run zget <url> --flat
uv run zget <url> -o /path/to/dir
uv run zget <url> --audio-only
uv run zget <url> --quality 720

# inspect without download
uv run zget info <url>
uv run zget info <url> --json --compact
uv run zget --list-formats <url>
uv run zget list-channel <channel-or-playlist-url> --since 2020-01-01 --jsonl

# library
uv run zget --search "query"
uv run zget --stats
uv run zget --doctor
uv run zget --doctor --fix                 # rewrite stale paths only
uv run zget paths check
uv run zget paths rewrite --dry-run
uv run zget paths rewrite

# config
uv run zget config show
uv run zget config set flat true
```

### C-SPAN

- `c-span.org/video/?...` works via yt-dlp as usual.
- `c-span.org/program/.../{id}` is supported: zget resolves public HLS and uses the required Referer headers.

### Path health

| Class | Meaning |
|-------|---------|
| healthy | File exists under ZGET_HOME |
| relocatable | Stale absolute path; file found after home/volume rename |
| off-home | File exists outside ZGET_HOME (e.g. `-o` pipeline output) |
| offline volume | Path on an unmounted `/Volumes/...` with no sibling match |
| orphan | File missing |

`--doctor --fix` rewrites relocatable paths. `--purge-orphans` deletes orphan DB rows only after you mean it.

## Web UI (optional)

```bash
uv run zget-server --port 9989 --open
# or double-click zget-start.command on macOS
```

Default: http://localhost:9989. Use `--secure` to allow localhost + Tailscale only when binding for LAN/mesh access.

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

Tools include download, search, get local path, extract info. Full contract for other projects: [docs/INTEGRATION.md](docs/INTEGRATION.md).

## Platforms

Verified in practice: YouTube, Instagram, X, TikTok, Reddit, Twitch, C-SPAN (including program pages). Many more via yt-dlp, untested.

## Layout

```text
src/zget/
  core.py           # yt-dlp download / extract
  platforms/        # adapters (C-SPAN program HLS)
  library/          # ingest, path migration, thumbnails
  cli.py            # CLI
  server/           # FastAPI + static Web Components UI
  mcp/              # MCP server
  db/               # SQLite FTS5
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
