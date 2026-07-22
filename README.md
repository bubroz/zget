# zget

The Archival Engine. Download and preserve media from YouTube, Instagram, TikTok, Reddit, X, Twitch, C-SPAN, and 600+ other sites in a local library you control.

![zget demo](assets/demo.gif)

## Why zget?

**The internet is ephemeral. Your library isn't.**

Content disappears constantly—videos get deleted, accounts get banned, platforms shut down. zget builds a personal archive with metadata, search, and optional media-server layout.

- **Save before it's gone** — tutorials, interviews, hearings, clips
- **Share without barriers** — offline copies past geo-blocks and login walls
- **Watch offline** — flights, travel, weak connectivity
- **Research** — archive footage before it changes or disappears
- **Household library** — one vault, optional Plex/Jellyfin-friendly layout
- **Agent-friendly** — CLI + MCP for handoff to transcription and analysis tools

## Requirements

- **macOS** (Apple Silicon or Intel) or **Linux**
- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)**
- **ffmpeg** (processing / HLS)

## Library location

Media and `library.db` live under **`ZGET_HOME`**:

| Layer | Path |
|-------|------|
| Config | `~/.config/zget/config.json` → key `zget_home` |
| Env | `ZGET_HOME=...` |
| Default | `~/Downloads/zget` if unset |

Example:

```json
{
  "zget_home": "/Volumes/Media/zget"
}
```

After upgrades, re-check config so a reset does not recreate the default unexpectedly.

Layout:

```text
$ZGET_HOME/
  library.db
  videos/<platform>/
  thumbnails/
  exports/
  logs/
```

## Installation

```bash
# uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# ffmpeg (macOS)
brew install ffmpeg

git clone https://github.com/bubroz/zget.git
cd zget
./zget-start.command   # installs deps, starts server, opens browser
```

Browser opens at `http://localhost:9989`.

## Daily use

### Web UI

Double-click **`zget-start.command`** (macOS) or run:

```bash
uv run zget-server --port 9989 --secure --open
```

Keep the terminal open so the process can use browser cookies (important for YouTube/TikTok).

Optional: access from phone via [Tailscale](https://tailscale.com) at `http://100.x.y.z:9989` (same account on both devices; use your Tailscale IPv4).

### CLI download

```bash
uv run zget <url>
uv run zget <url> --output /path/to/dir
uv run zget <url> --flat              # no platform subdirectory
uv run zget <url> --audio-only -a
uv run zget <url> --quality 720
uv run zget <url> --quiet
```

## Features

- **Multi-platform download** via yt-dlp (600+ sites)
- **C-SPAN program pages** — `c-span.org/program/.../{id}` via public HLS when needed
- **Full-text search** (SQLite FTS5)
- **Metadata + NFO + thumbnails** for archival / Plex / Jellyfin
- **Dedup** by URL and file hash
- **Path health** — migrate after moving `ZGET_HOME` or renaming volumes
- **MCP tools** for AI agents (search, download, local path handoff)

Downstream / agent integration: **[docs/INTEGRATION.md](docs/INTEGRATION.md)**.

## Verified platforms

| Platform  | Status |
|-----------|--------|
| YouTube   | Verified |
| Instagram | Verified |
| X         | Verified |
| TikTok    | Verified |
| Reddit    | Verified |
| Twitch    | Verified |
| C-SPAN    | Verified, including `/program/.../{id}` HLS |

Other sites may work via yt-dlp without being formally tested.

**C-SPAN notes:** classic `c-span.org/video/?…` uses yt-dlp. Program pages are resolved to public HLS with required Referer headers when the native extractor cannot handle the page.

## CLI reference

### Library

```bash
uv run zget --search "<query>"       # full-text search
uv run zget --stats                  # counts and size
uv run zget --doctor                 # path health (healthy / relocatable / off-home / offline volume / orphan)
uv run zget --doctor --fix           # rewrite stale paths only (safe)
uv run zget --doctor --fix --purge-orphans   # also drop truly missing records
uv run zget --doctor --fix --purge-orphans --dry-run
uv run zget paths check
uv run zget paths rewrite --dry-run
uv run zget paths rewrite            # apply; creates a library.db backup first
```

**Path classes (important):**

| Class | Meaning |
|-------|---------|
| healthy | File exists at stored path under `ZGET_HOME` |
| relocatable | Stale path; file found under current home or renamed volume |
| off-home | File exists outside `ZGET_HOME` (intentional pipeline `-o`) |
| offline volume | `/Volumes/X/...` unmounted and no sibling match — do not purge blindly |
| orphan | File missing (only these are removed by `--purge-orphans`) |

### Metadata (no download)

```bash
uv run zget info <url>
uv run zget info <url> --json
uv run zget info <url> --json --compact
uv run zget --list-formats <url>
uv run zget list-channel <channel-or-playlist-url>
uv run zget list-channel <url> --since 2020-01-01 --jsonl --limit 500
```

### Configuration

```bash
uv run zget config show
uv run zget config set <key> <value>
uv run zget config unset <key>
```

| Key | Description | Example |
|-----|-------------|---------|
| `zget_home` | Library root | `/Volumes/Media/zget` |
| `output_dir` | Override download directory | `/Volumes/Media/Videos` |
| `flat` / flat structure | Skip platform subdirs | `true` |
| `template` | Filename template | `%(upload_date>%Y-%m-%d)s %(title)s.%(ext)s` |

Plex-style flat library:

```bash
uv run zget config set output_dir "/Volumes/Media/Social Videos"
uv run zget config set flat true
```

## AI agents (MCP)

```bash
uv run zget-mcp
```

Example agent config:

```json
{
  "mcpServers": {
    "zget": {
      "command": "uv",
      "args": ["run", "zget-mcp"],
      "cwd": "/path/to/your/zget",
      "env": {
        "PATH": "/opt/homebrew/bin:/usr/bin:/bin"
      }
    }
  }
}
```

| Tool | Description |
|------|-------------|
| `zget_download` | Download from URL |
| `zget_search` | Full-text search |
| `zget_get_video` | Metadata by DB id |
| `zget_get_local_path` | On-disk path for other tools |
| `zget_extract_info` | Metadata without download |
| `zget_list_formats` | Formats list |
| `zget_check_url` | Already in library? |
| `zget_get_recent` | Recent downloads |
| `zget_get_by_uploader` | By channel/uploader |

Prefer resolving library paths via config/`ZGET_HOME`, not hardcoded `~/Downloads/zget`. Details: [docs/INTEGRATION.md](docs/INTEGRATION.md).

## Troubleshooting

### TikTok connection refused

Router/Pi-hole may block TikTok CDN CNAMEs. Whitelist as needed, e.g.:

- `vm.tiktok.com.edgesuite.net`
- `www.tiktok.com.edgesuite.net`
- `a2047.r.akamai.net`

### Port in use

```bash
lsof -i :9989
uv run zget-server --port 8080
```

### Mobile / Tailscale

1. `tailscale status` on both devices  
2. Same account  
3. Open `http://100.x.y.z:9989` (your machine’s Tailscale IPv4)

### Library moved or disk renamed

```bash
uv run zget paths check
uv run zget paths rewrite --dry-run
uv run zget paths rewrite
```

Do not run `--purge-orphans` until offline volumes and path rewrites are sorted out.

## Architecture

```text
src/zget/
├── server/           # FastAPI + native Web Components UI (static/)
├── mcp/              # Model Context Protocol server
├── library/          # ingest, paths, export, thumbnails
├── platforms/        # platform adapters (e.g. C-SPAN program HLS)
├── queue/            # async download queue
├── db/               # SQLite FTS5 (async + sync stores)
├── metadata/         # NFO sidecars
├── commands/         # CLI subcommands (config, …)
├── core.py           # yt-dlp download / extract_info
├── config.py         # paths and settings
├── types.py          # YtdlpInfo, ProgressDict
├── cookies.py        # browser cookie extraction
├── net.py            # Tailscale IP for secure mesh
├── health.py         # diagnostics
├── smokescreen.py    # site health checks
├── regions.py        # regional collections
├── safe_delete.py    # trash-based deletes
├── utils.py
└── cli.py
```

Web UI is **framework-free** (native Web Components, no frontend build step).

## Development

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src
```

## Acknowledgments

Built on [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## License

MIT
