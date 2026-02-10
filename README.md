# zget

The Archival Engine. Download and preserve media from YouTube, Instagram, TikTok, Reddit, X, Twitch, C-SPAN, and 600+ other sites to your own local library.

![zget demo](assets/demo.gif)

## Why zget?

**The internet is ephemeral. Your library isn't.**

Content disappears constantly—videos get deleted, accounts get banned, platforms shut down. zget lets you build a personal archive that you control.

- **Save before it's gone.** That tutorial you keep referencing, that interview, that viral clip
- **Share without barriers.** Send videos to people who can't access the original (geo-blocks, login walls)
- **Watch offline.** Download for flights, road trips, anywhere with bad connectivity
- **Research and journalism.** Archive footage before it gets altered or removed
- **Family media server.** One household library accessible from every device

## Requirements

- **macOS** (Apple Silicon or Intel) or **Linux**
- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)** (fast Python package manager)
- **ffmpeg** (for video processing)

## Installation

### 1. Install Dependencies

```bash
# Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install ffmpeg (macOS)
brew install ffmpeg
```

### 2. Clone the Repository

```bash
git clone https://github.com/bubroz/zget.git
cd zget
```

### 3. First Run (Setup)

```bash
# This installs all Python dependencies automatically
./zget-start.command
```

Your browser will open to `http://localhost:9989`. You're ready to archive!

## Quick Start (Robust Launcher)

We recommend using the included **Launcher Script** for daily use.

### 1. Daily Use

Double-click `zget-start.command` in Finder.

This will:

1. Open a terminal window (keep this open!)
2. Start the server on port **9989**
3. Securely bind to your Tailscale network
4. Launch your browser automatically

> **Why keep the window open?**
> Running in a visible terminal ensures zget has permission to use your browser's cookies. This is critical for downloading from sites like TikTok and YouTube which block background bots.

### 2. Mobile Access (Tailscale)

To access your library from your phone (e.g. while away from home), use [Tailscale](https://tailscale.com).

1. **Install Tailscale** on both your Mac and your Phone.
2. **Log in** to the same account.
3. **Visit** the server IP from your phone:

    ```
    http://100.x.y.z:9989
    ```

    *(Find your Mac's Tailscale IP in the Tailscale menu bar icon)*

## Features

### Core

- **Multi-Platform Downloads**: YouTube, Instagram, TikTok, Reddit, Twitch, X, and 600+ sites via yt-dlp
- **Full-Text Search**: Find videos by title, uploader, or description (SQLite FTS5)
- **Metadata Preservation**: Original titles, upload dates, view counts, descriptions
- **H.264 Transcoding**: Automatic conversion for iOS/Safari compatibility
- **Duplicate Detection**: By URL and file hash

### Media Server Integration (Plex / Jellyfin)

- **Custom Output Directory**: Point downloads directly at your library folder
- **Flat Structure**: Skip platform subdirectories for watch-folder scanning
- **NFO Sidecar Generation**: Kodi-style XML metadata files
- **Local Thumbnails**: Poster images placed alongside videos

## Verified Platforms

| Platform  | Status |
|-----------|--------|
| YouTube   | ✅ Verified |
| Instagram | ✅ Verified |
| X         | ✅ Verified |
| TikTok    | ✅ Verified |
| Reddit    | ✅ Verified |
| Twitch    | ✅ Verified |
| C-SPAN    | ✅ Verified |

Additional sites may work via [yt-dlp](https://github.com/yt-dlp/yt-dlp) but are not officially tested.

## CLI Reference

### Download a Video

```bash
uv run zget <url>                    # Download to default location
uv run zget <url> --output /path     # Download to specific directory
uv run zget <url> --flat             # Skip platform subdirectory
```

### Library Commands

```bash
uv run zget search <query>           # Full-text search
uv run zget stats                    # Library statistics
uv run zget doctor                   # Health check (find orphans, verify files)
uv run zget doctor --fix             # Auto-fix issues
uv run zget formats <url>            # List available formats without downloading
```

### Configuration

Persistent settings stored in `~/.config/zget/config.json`:

```bash
uv run zget config show              # View current settings
uv run zget config set <key> <value> # Set a value
uv run zget config unset <key>       # Remove a value
```

Common keys:

| Key | Description | Example |
|-----|-------------|---------|
| `output_dir` | Custom output path | `/Volumes/Media/Videos` |
| `flat` | Skip platform subdirs | `true` |
| `template` | Filename format | `%(upload_date>%Y-%m-%d)s %(title)s.%(ext)s` |

### Plex Setup Example

```bash
uv run zget config set output_dir "/Volumes/Media/Social Videos"
uv run zget config set flat true
```

Videos will now download directly to your Plex library with proper metadata (NFO) and artwork generated automatically.

## AI Agent Integration (MCP)

zget exposes tools for AI agents via the Model Context Protocol.

### Available Tools

| Tool | Description |
|------|-------------|
| `zget_download` | Download a video from URL |
| `zget_search` | Full-text search the library |
| `zget_get_video` | Get metadata by video ID |
| `zget_get_local_path` | Get filesystem path for a video |
| `zget_extract_info` | Extract metadata without downloading |
| `zget_list_formats` | List available formats |
| `zget_check_url` | Check if URL exists in library |
| `zget_get_recent` | Get recently downloaded videos |
| `zget_get_by_uploader` | Get videos by uploader/channel |

### Configuration

Add this to your agent's MCP config (e.g., `claude_desktop_config.json`):

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

Replace `/path/to/your/zget` with the actual path where you cloned the repository.

### Run Standalone

```bash
uv run zget-mcp
```

## Troubleshooting

### "Connection Refused" on TikTok

If TikTok downloads fail with `0.0.0.0` or `Connection Refused`, check your Pi-hole or router. TikTok uses CNAME chains that may be blocked.

**Required whitelist domains:**

- `vm.tiktok.com.edgesuite.net`
- `www.tiktok.com.edgesuite.net`
- `a2047.r.akamai.net`

### Server Not Starting

Check if another process is using port 9989:

```bash
lsof -i :9989
```

Kill the conflicting process or use a different port:

```bash
uv run zget-server --port 8080
```

### Mobile Can't Connect

1. Verify Tailscale is running: `tailscale status`
2. Ensure both devices are logged into the same Tailscale account
3. Try accessing via IP instead of hostname: `http://100.x.y.z:9989`

## Architecture

```
src/zget/
├── server/       # FastAPI backend + Web Components frontend
├── mcp/          # Model Context Protocol server
├── library/      # Video ingest pipeline (ingest, export, thumbnails)
├── queue/        # Async download queue manager
├── db/           # SQLite FTS5 database + Pydantic models
├── metadata/     # NFO sidecar generation
├── commands/     # CLI subcommands
├── core.py       # yt-dlp wrapper (download, extract_info)
├── config.py     # Centralized configuration and path constants
├── health.py     # Self-diagnostics and health logging
├── utils.py      # Shared utilities (sanitize_filename, MIME)
└── cli.py        # Main CLI entry point
```

## Acknowledgments

zget is built on [yt-dlp](https://github.com/yt-dlp/yt-dlp) and was developed with assistance from Gemini.

## License

MIT
