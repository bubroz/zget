# zget

Personal media archival. Download videos from YouTube, Instagram, TikTok, Reddit, X, Twitch, C-SPAN, and 600+ other sites to your own library.

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
- **Python 3.11+**
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

### 3. First Run

```bash
# This installs all Python dependencies automatically
uv run zget-server --open
```

Your browser will open to `http://localhost:8000`. You're ready to archive!

## Quick Start

### Option A: Background Service (Recommended)

Run zget silently in the background, starting automatically when you log in:

```bash
# Copy and customize the launch agent
cp com.bubroz.zget.plist.template ~/Library/LaunchAgents/com.bubroz.zget.plist

# Edit the file to set YOUR path (replace YOUR_USERNAME)
nano ~/Library/LaunchAgents/com.bubroz.zget.plist

# Start the service
launchctl load ~/Library/LaunchAgents/com.bubroz.zget.plist
```

**Verification:** Open `http://localhost:8000` in your browser.

### Option B: Manual Launcher

Double-click `zget-start.command` in Finder to run temporarily.

### Option C: Terminal

```bash
uv run zget-server --open
```

## Mobile Access (From Your Phone)

zget includes a **Secure Mesh** feature that lets you access your library from your phone—even when you're not at home.

### How It Works

zget uses [Tailscale](https://tailscale.com) (a free VPN) to create a private network between your devices. Your server is invisible to public Wi-Fi but fully accessible to your authenticated devices.

### Setup

1. **Install Tailscale on your Mac:**

   ```bash
   brew install tailscale
   tailscale up --hostname=zget
   ```

2. **Install Tailscale on your phone:**
   - [iOS App Store](https://apps.apple.com/app/tailscale/id1470499037)
   - [Google Play Store](https://play.google.com/store/apps/details?id=com.tailscale.ipn)

3. **Log in with the same account** on both devices.

4. **Access zget:**
   - From your phone's browser: `http://zget:8000`
   - Tap "Add to Home Screen" for a native app experience

### Security Notes

- **Localhost always works:** You can always access zget at `http://localhost:8000` from the Mac itself.
- **Tailscale required for remote:** Your phone needs Tailscale connected to reach the server.
- **Public networks blocked:** Anyone on public Wi-Fi cannot see your server.

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

Check if another process is using port 8000:

```bash
lsof -i :8000
```

Kill the conflicting process or use a different port:

```bash
uv run zget-server --port 8080
```

### Mobile Can't Connect

1. Verify Tailscale is running: `tailscale status`
2. Ensure both devices are logged into the same Tailscale account
3. Try accessing via IP instead of hostname: `http://100.x.y.z:8000`

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

zget is built on [yt-dlp](https://github.com/yt-dlp/yt-dlp) and was developed with assistance from Gemini.

## License

MIT
