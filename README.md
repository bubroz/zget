# zget: The Archival Intelligence Engine

`zget` is a high-fidelity media archival engine and headless server designed for building persistent video libraries. It leverages `yt-dlp`'s **1,899 extractors** and provides a modern, touch-friendly **Webport** (PWA) for managing downloads on mobile and desktop.

## Features

- **Headless Archival Server**: A robust FastAPI engine that manages complex background downloads independently of the UI.
- **Webport (PWA)**: A premium, StoryTime-inspired web interface with:
  - **Share Sheet Support**: Archiving directly from mobile share sheets.
  - **Camera Roll Ingestion**: Direct-to-device video downloads.
  - **Glassmorphism UI**: High-fidelity dark mode with real-time progress.
- **Site Intelligence**: Deep Registry covering 1,899+ sites with active health monitoring.
- **SQLite Library**: Fast, searchable database (FTS5) for your entire collection.
- **MCP Native**: First-class support for AI agents (e.g., Librarian) via the Model Context Protocol.

## Installation

```bash
git clone https://github.com/bubroz/zget.git
cd zget
uv sync
```

## Quick Start

### 1. Start the Server

```bash
uv run zget-server --port 8080
```

### 2. Open the Webport

Access `http://localhost:8080` (or your local IP) in any browser. On mobile, "Add to Home Screen" to install the PWA.

### 3. CLI Lightning Downloads

```bash
zget <url>
```

## Architecture

```
src/zget/
├── server/         # FastAPI backend & PWA static files
├── mcp/            # MCP server for agent integration
├── core.py         # The Archival Engine (yt-dlp wrapper)
├── db/             # SQLite persistence layer
├── health.py       # Site verification (Smokescreen Engine)
└── cli.py          # Unified entry point & status dashboard
```

## MCP Tools

| Tool | Action |
|------|--------|
| `zget_download` | Command the archivist to ingestion a URL |
| `zget_search` | Query the local library |
| `zget_get_local_path` | Handoff file paths to other agents |

## License

MIT
