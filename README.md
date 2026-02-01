# zget

Personal media archival. Download videos from YouTube, Instagram, TikTok, Reddit, X, Twitch, CNET, and 600+ other sites to your own library.

![zget demo](assets/demo.gif)

## Why zget?

**The internet is ephemeral. Your library isn't.**

Content disappears constantly—videos get deleted, accounts get banned, platforms shut down. zget lets you build a personal archive that you control.

- **Save before it's gone.** That tutorial you keep referencing, that interview, that viral clip
- **Share without barriers.** Send videos to people who can't access the original (geo-blocks, login walls, or grandma doesn't "do" TikTok)
- **Watch offline.** Download for flights, road trips, anywhere with bad connectivity
- **Research and journalism.** Archive footage before it gets altered or removed
- **Family media server.** One household library accessible from every device

## Features

### Core

- **Multi-Platform Downloads**: YouTube, Instagram, TikTok, Reddit, Twitch, X, and 600+ sites via yt-dlp
- **Full-Text Search**: Find videos by title, uploader, or description (SQLite FTS5)
- **Metadata Preservation**: Original titles, upload dates, view counts, descriptions
- **H.264 Transcoding**: Automatic conversion for iOS/Safari compatibility
- **Duplicate Detection**: By URL and file hash

### Media Server Integration (Plex / Jellyfin / Emby)

- **Custom Output Directory**: Point downloads directly at your library folder
- **Flat Structure**: Skip platform subdirectories for watch-folder scanning
- **NFO Sidecar Generation**: Kodi-style XML metadata files so Plex identifies social media correctly
- **Local Thumbnails**: Poster images placed alongside videos for automatic artwork
- **Atomic Move**: Downloads complete in temp before moving, preventing partial scans

### Interfaces

- **Web Dashboard**: Responsive PWA with real-time progress, platform icons, search
- **CLI**: Direct downloads, library management, health checks
- **MCP Server**: AI agent integration via Model Context Protocol

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

## Quick Start

### 1. Bootstrap

```bash
make bootstrap
```

Installs [uv](https://docs.astral.sh/uv/) and sets up dependencies.

### 2. Start the Server

```bash
make serve
```

Or manually:

```bash
uv run zget-server --port 8000 --host 0.0.0.0
```

### 3. Open the App

Access `http://localhost:8000` in your browser. Tap **Add to Home Screen** on iOS for the full PWA experience.

> **Safari Users:** Always use `localhost:8000`—Safari doesn't resolve `0.0.0.0`.

## CLI Reference

### Download a Video

```bash
zget <url>                    # Download to default location
zget <url> --output /path     # Download to specific directory
zget <url> --flat             # Skip platform subdirectory
```

### Library Commands

```bash
zget search <query>           # Full-text search
zget stats                    # Library statistics
zget doctor                   # Health check (find orphans, verify files)
zget doctor --fix             # Auto-fix issues
zget formats <url>            # List available formats without downloading
```

### Configuration

Persistent settings stored in `~/.config/zget/config.json`:

```bash
zget config show              # View current settings
zget config set <key> <value> # Set a value
zget config unset <key>       # Remove a value
```

Common keys:

| Key | Description | Example |
|-----|-------------|---------|
| `output_dir` | Custom output path | `/Volumes/Media/Videos` |
| `flat` | Skip platform subdirs | `true` |
| `template` | Filename format | `%(upload_date>%Y-%m-%d)s %(title)s.%(ext)s` |

### Plex Setup Example

```bash
zget config set output_dir "/Volumes/Media/Social Videos"
zget config set flat true
zget config set template "%(upload_date>%Y-%m-%d)s %(extractor)s - %(uploader).50s - %(title).100s.%(ext)s"
```

Videos will now download directly to your Plex library with proper metadata (NFO) and artwork (thumbnails) generated automatically.

## MCP Integration

zget exposes tools for AI agents via the Model Context Protocol:

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

Run the MCP server:

```bash
uv run python -m zget.mcp.server
```

## Architecture

```
src/zget/
├── server/       # FastAPI backend + Web Components frontend
├── mcp/          # Model Context Protocol server
├── library/      # Video ingest pipeline
├── db/           # SQLite FTS5 database
├── metadata/     # NFO generation
├── commands/     # CLI subcommands
├── core.py       # yt-dlp wrapper
└── cli.py        # Main CLI entry point
```

## Acknowledgments

zget is built on [yt-dlp](https://github.com/yt-dlp/yt-dlp) and was developed with assistance from [Gemini](https://deepmind.google/technologies/gemini/).

## License

MIT
