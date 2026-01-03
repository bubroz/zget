# zget: The Archival Engine

`zget` is a high-fidelity media archival system built for the Digital Intelligence Ecosystem. It operates through a specialized triad: **The Archivist** (Ingestion), **The Vault** (Persistence), and **The Portal** (Discovery).

## The Triad

- **The Archivist (Server)**: A robust FastAPI engine that manages complex extraction and background downloads independently.
- **The Vault (Library)**: A persistent SQLite-backed repository (FTS5) designed for high-fidelity, metadata-rich media storage.
- **The Portal (PWA)**: A premium, glassmorphism-inspired web interface with:
  - **Integrated Player**: Native iOS/Mobile playback for archived H.264 content with full range-seek support.
  - **Share Sheet Native**: Archive directly from mobile share sheets (iOS/Android).
  - **Integrity Repair**: Automatic background transcoding of incompatible codecs (VP9/AV1) to maintain Vault health.

## Features

- **Site Intelligence**: Deep Registry covering 1,899+ sites with automated smokescreen health monitoring.
- **H.264 Standard**: Universal compatibility by prioritizing iOS-friendly codecs for all ingestion.
- **MCP Native**: First-class support for AI agents (e.g., Librarian) via the Model Context Protocol.

## Installation

```bash
git clone https://github.com/bubroz/zget.git
cd zget
uv sync
```

## Quick Start

### 1. Wake The Archivist

```bash
uv run zget-server --port 8000 --host 0.0.0.0
```

### 2. Enter The Portal

Access `http://<local-ip>:8000` in any browser. Tap **"Add to Home Screen"** on iOS to install the standalone Portal experience.

### 3. CLI Ingestion

```bash
zget <url>
```

## Architecture

```
src/zget/
├── server/         # The Portal (FastAPI & PWA)
├── mcp/            # MCP server for agentic handoffs
├── core.py         # The Archivist (Archival Engine)
├── db/             # The Vault (SQLite FTS5)
├── health.py       # Smokescreen Verification Engine
└── cli.py          # Unified entry point & status
```

## MCP Tools (The Archivist)

| Tool | Action |
|------|--------|
| `zget_download` | Command the archivist to ingest a URL |
| `zget_search` | Query the vault |
| `zget_get_local_path` | Handoff file paths to other agents |

## Roadmap

| Status | Feature | Description |
|--------|---------|-------------|
| 🔜 | **Subscription Feeds** | Auto-monitor channels/playlists for new uploads and archive automatically. |
| 🔜 | **Watch Party Mode** | Sync playback across multiple devices on the LAN. |
| 📋 | **iOS Shortcut Integration** | Deep linking via `zget://` URL scheme for one-tap archival. |
| 📋 | **Transcript Extraction** | Archive subtitles using Whisper or native yt-dlp transcripts. |
| 📋 | **IPTV Export** | Generate M3U playlists for The Vault (VLC/Plex compatible). |
| 💡 | **Multi-Region Health Check** | Proxy-based verification for geo-blocked site health. |
| 💡 | **Librarian Handoff v2** | Full multimodal indexing: frames, faces, and voiceprints. |

## Credits & Acknowledgments

`zget` is built on the shoulders of others:

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)**: The unparalleled extraction engine that powers The Archivist's 1,899+ site capacity.
- **[FastAPI](https://fastapi.tiat.io/)**: The high-performance server framework driving The Archivist.
- **[SQLite](https://www.sqlite.org/)**: The robust engine behind the persistence layer (The Vault).
- **[Vanilla JS/CSS](https://developer.mozilla.org/)**: Powering the high-fidelity, glassmorphism Portal experience without dependency bloat.

## License

MIT
