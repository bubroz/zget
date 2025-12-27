# Project Context: The Archivist's Terminal

## Purpose

zget is a modern, high-fidelity TUI and SQLite-backed archival engine for video downloads. It focuses on building a persistent library through direct yt-dlp extraction.

## Tech Stack

- **Python 3.10+**: Core language
- **yt-dlp**: Extraction engine
- **Textual**: TUI Framework
- **SQLite (FTS5)**: Metadata and Library storage
- **uv**: Dependency management

## Project Conventions

### Code Style

- **Type hints**: Required on all functions
- **Docstrings**: Google-style
- **Line length**: 100 chars
- **Linting**: Ruff

### API Design

- **Simple defaults**: `download(url)` should just work
- **Progressive complexity**: Options for power users
- **No surprises**: Predictable output paths and formats

### Authentication

- **Cookies only**: No username/password (platforms ban this)
- **Browser extraction**: `--cookies-from chrome` pattern
- **Cookie files**: Netscape format for manual control

## Supported Platforms

| Platform | Auth Required | Method |
|----------|---------------|--------|
| YouTube | No (public) / Yes (private) | Cookies |
| Instagram | Yes (most content) | Cookies |
| TikTok | No (public) / Yes (private) | Cookies |
| Twitter/X | Yes (most content) | Cookies |
| Reddit | No | - |
| Vimeo | No (public) | Cookies |

- **The Archivist's Terminal**: Not just a downloader, a workstation for media preservation.
- **Local Sovereignty**: All data (DB, files, history) lives on the user's machine.
- **Modern Vintage Aesthetic**: High-quality visual design in a terminal environment.
- **Site Intelligence**: Deep integration with yt-dlp extractor health.
