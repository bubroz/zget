# zget: The Archivist's Terminal

`zget` is a modern, high-fidelity terminal user interface (TUI) and SQLite-backed archival engine for video downloads. Built on top of `yt-dlp`, it focuses on building a persistent library rather than just ephemeral downloads.

## Features

- **The Archivist's Terminal:** A "modern vintage" TUI for managing your media collections
- **Unified Workflow:** Integrated URL entry, background download queue, and library browser
- **Site Intelligence:** Deep Registry covering **1,899 extractors** with curated metadata:
  - 100% high-confidence categorization
  - 63 countries represented
  - 96% test URL coverage for health monitoring
- **SQLite Library:** Fast, searchable database (FTS5) of all your downloads
- **Privacy First:** All data is stored locally. No telemetry, no cloud tracking
- **High-Performance Engine:** Optimized for M3 Max and high-speed connections

## Registry Statistics

| Metric | Value |
|--------|-------|
| Total Extractors | 1,899 |
| Categories | 9 |
| Countries | 63 |
| Test URL Coverage | 96.2% |
| Confidence | 100% High |

### Category Breakdown

| Category | Count | % |
|----------|-------|---|
| Entertainment/VOD | 660 | 34.8% |
| Social/Community | 338 | 17.8% |
| News/Journalism | 229 | 12.1% |
| Music/Audio | 209 | 11.0% |
| Tools/Software | 167 | 8.8% |
| Education/EdTech | 147 | 7.7% |
| Adult/NSFW | 88 | 4.6% |
| Sports | 57 | 3.0% |

## Installation

```bash
pipx install git+https://github.com/bubroz/zget.git
```

## Usage

Run the TUI:

```bash
zget
```

### Keybindings

| Key | Action |
|-----|--------|
| `D` | Focus URL Input |
| `Enter` | Submit URL / Play Video |
| `/` | Search Library |
| `R` | Open Site Registry |
| `Esc` | Clear focus / Go back |
| `Q` | Quit |

## Development

`zget` uses `uv` for dependency management.

```bash
git clone https://github.com/bubroz/zget.git
cd zget
uv venv
uv sync
```

## Architecture

```
src/zget/
├── cli.py          # Command-line interface
├── core.py         # Download engine (yt-dlp wrapper)
├── config.py       # Configuration management
├── health.py       # Site health monitoring
├── db/             # SQLite database layer
├── library/        # Media library management
├── queue/          # Background download queue
├── mcp/            # MCP server for agent integration
│   ├── server.py   # JSON-RPC over stdio
│   └── tools.py    # Tool implementations
└── tui/            # Textual-based TUI
    ├── app.py      # Main application
    └── screens/    # Screen components
```

## MCP Server (Agent Integration)

zget includes an MCP (Model Context Protocol) server that allows AI agents to access the video library programmatically.

### Start the MCP Server

```bash
zget-mcp
```

### Available Tools

| Tool | Description |
|------|-------------|
| `zget_download` | Download a video to the library |
| `zget_search` | Full-text search across library |
| `zget_get_video` | Get full video metadata by ID |
| `zget_get_local_path` | Get file path for a video |
| `zget_extract_info` | Extract metadata without downloading |
| `zget_list_formats` | List available formats |
| `zget_check_url` | Check if URL already exists |
| `zget_get_recent` | Get recently downloaded videos |
| `zget_get_by_uploader` | Get videos by uploader |

### Use with Antigravity

Add to your MCP configuration:

```json
{
  "mcpServers": {
    "zget": {
      "command": "zget-mcp"
    }
  }
}
```

## Acknowledgments

zget is built on the shoulders of giants:

- **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** — The incredible extraction engine that powers all 1,899 site integrations. This project wouldn't exist without the yt-dlp team and community.
- **[Textual](https://github.com/Textualize/textual)** — The modern TUI framework that enables the "Archivist's Terminal" experience.
- **[Rich](https://github.com/Textualize/rich)** — Beautiful terminal formatting.

The enriched registry metadata was curated using site data from yt-dlp extractors, enhanced with category, country, and description information.

## License

MIT
