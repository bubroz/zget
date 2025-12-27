# zget: The Archivist's Terminal

`zget` is a modern, high-fidelity terminal user interface (TUI) and SQLite-backed archival engine for video downloads. Built on top of `yt-dlp`, it focuses on building a persistent library rather than just ephemeral downloads.

## Features

- **The Archivist's Terminal:** A "modern vintage" TUI for managing your media collections.
- **Unified Workflow:** Integrated URL entry, background download queue, and library browser in a single screen.
- **Site Intelligence:** Built-in "Integrity Matrix" that pulls real-time health data for ~1,500 supported sites from the `yt-dlp` project.
- **SQLite Library:** Fast, searchable database (FTS5) of all your downloads with uploader, platform, and size metadata.
- **Privacy First:** All data is stored locally. No telemetry, no cloud tracking.
- **High-Performance Engine:** Optimized for M3 Max and high-speed connections with intelligent rate-limit tracking.

## Installation

```bash
pipx install git+https://github.com/[YOUR-USERNAME]/zget.git
```

## Usage

Run the TUI:

```bash
zget
```

### Keybindings

- `D`: Focus URL Input
- `Enter`: Submit URL / Play Video in Library
- `/`: Search Library
- `R`: Open Site Registry (Browses all 1,500+ supported sites)
- `Esc`: Clear focus / Go back
- `Q`: Quit

## Development

`zget` uses `uv` for dependency management.

```bash
git clone https://github.com/[YOUR-USERNAME]/zget.git
cd zget
uv venv
uv sync
```

## License

MIT
