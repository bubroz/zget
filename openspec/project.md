# Project Context: The Archivist's Terminal

## Purpose

zget is a modern, high-fidelity TUI and SQLite-backed archival engine for video downloads. It focuses on building a persistent library through direct yt-dlp extraction with deep site intelligence.

## Tech Stack

- **Python 3.10+**: Core language
- **yt-dlp**: Extraction engine (1,899 supported extractors)
- **Textual**: TUI Framework
- **SQLite (FTS5)**: Metadata and Library storage
- **uv**: Dependency management

## Architecture Overview

```
src/zget/
├── cli.py          # CLI entry point with rich argument parsing
├── core.py         # Download engine wrapping yt-dlp
├── config.py       # Configuration and paths
├── health.py       # Site health monitoring engine
├── cookies.py      # Browser cookie extraction
├── db/
│   └── store.py    # SQLite database operations
├── library/        # Media library management
├── queue/
│   └── manager.py  # Background download queue
└── tui/
    ├── app.py      # Main Textual application
    ├── styles/     # TCSS stylesheets (retro aesthetic)
    └── screens/
        ├── main.py     # Unified main screen
        └── registry.py # Site registry browser
```

## Data Assets

```
data/
├── enriched_registry.json  # 1,899 extractors with metadata
│   ├── Categories (9): VOD, Social, News, Music, Tools, Education, Adult, Sports, Lifestyle
│   ├── Countries (63): US, DE, CN, RU, JP, GB, FR, IN, etc.
│   └── Confidence: 100% High
└── test_videos.json        # Test video registry for health checks
```

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

## Supported Platforms (Top Categories)

| Category | Examples | Count |
|----------|----------|-------|
| Entertainment/VOD | YouTube, Netflix, Disney+, HBO | 660 |
| Social/Community | TikTok, Instagram, Twitter, Reddit | 338 |
| News/Journalism | BBC, CNN, Al Jazeera, Reuters | 229 |
| Music/Audio | Spotify, SoundCloud, Bandcamp | 209 |

## Design Principles

- **The Archivist's Terminal**: Not just a downloader, a workstation for media preservation
- **Local Sovereignty**: All data (DB, files, history) lives on the user's machine
- **Modern Vintage Aesthetic**: High-quality visual design in a terminal environment
- **Site Intelligence**: Deep integration with yt-dlp extractor health and metadata
