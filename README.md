# zget : The Archival Engine

`zget` is a personal media archival system. Download videos from YouTube, Instagram, TikTok, Reddit, and many other sites to your own library.

![zget demo](assets/demo.gif)

## Why zget?

**The internet is ephemeral. Your library isn't.**

Social media content disappears constantly. Videos get deleted, accounts get banned, platforms change policies or shut down entirely. zget lets you build a personal archive that you actually control.

### Use Cases

- **Save before it's gone.** That perfect tutorial, that interview you keep referencing, that viral clip about to get DMCA'd
- **Share without barriers.** Send videos to friends and family who can't access the original platform. Whether it's geo-restrictions, government censorship, login walls, or grandma just doesn't "do" TikTok
- **Watch offline.** Download for flights, road trips, or anywhere with spotty connectivity
- **Research and journalism.** Archive footage and evidence before it gets altered or removed
- **Family media server.** One household library accessible by everyone's devices

### Why not just use the platform?

- **One tool for many sites.** No more juggling different apps for each platform
- **Mobile-native.** Share sheet integration on iOS and Android
- **Metadata preserved.** Original titles, upload dates, view counts, and full-text search
- **Self-hosted.** Your data stays on your hardware. No subscriptions, no cloud dependency

## Features

- **Web Dashboard**: A clean, responsive interface built with native Web Components. No build step required.
- **Real-Time Progress**: Live download status with speed metrics and error reporting
- **Platform Detection**: Automatic recognition of source platforms with visual icons
- **Full-Text Search**: Find videos by title, uploader, or description
- **H.264 Transcoding**: Automatic conversion for universal iOS/Safari compatibility
- **Mobile PWA**: Add to home screen for a native app experience
- **MCP Server**: First-class support for AI agents via the Model Context Protocol

## Verified Platforms

Extensively tested and verified working:

| Platform | Status |
| -------- | ------ |
| YouTube | ✅ Verified |
| Instagram | ✅ Verified |
| X (Twitter) | ✅ Verified |
| TikTok | ✅ Verified |
| Reddit | ✅ Verified |
| Twitch | ✅ Verified |

Additional sites may work via [yt-dlp](https://github.com/yt-dlp/yt-dlp) but are not officially tested.

## Quick Start

### 1. Start the Server

```bash
# Recommended: Use uv for dependency management
uv run zget-server --port 8000 --host 0.0.0.0
```

### 2. Open the App

Access `http://localhost:8000` in any browser. Tap **"Add to Home Screen"** on iOS for the full experience.

## Architecture

```
src/zget/
├── server/     # FastAPI backend + Web Components frontend
├── mcp/        # Model Context Protocol server
├── library/    # Video storage and metadata
├── db/         # SQLite FTS5 database
├── core.py     # yt-dlp wrapper
└── cli.py      # Command-line interface
```

## Roadmap

| Status | Feature | Description |
| ------ | ------- | ----------- |
| 🔜 | Subscription Feeds | Auto-monitor channels for new content |
| 🔜 | Watch Party | Sync playback across LAN devices |
| 📋 | iOS Shortcuts | Deep linking via `zget://` URL scheme |
| 📋 | Transcripts | Subtitle extraction via Whisper |

## Acknowledgments

`zget` is made possible by the incredible work of the [yt-dlp](https://github.com/yt-dlp/yt-dlp) community and was built with assistance from [Gemini](https://deepmind.google/technologies/gemini/).

## License

MIT
