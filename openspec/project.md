# Project Context: zget Archival Engine

## Purpose

`zget` is a high-fidelity media archival system that decouples extraction logic (Headless Server) from management (Webport PWA) and automated integration (MCP).

## Tech Stack

- **FastAPI**: Core server infrastructure
- **yt-dlp**: Extraction engine (1,899 extractors)
- **Vanilla CSS/JS**: Premium glassmorphism Webport
- **SQLite (FTS5)**: Metadata and Library persistence
- **MCP**: Model Context Protocol for agentic handoffs

## Architecture

```
src/get/
├── server/
│   ├── app.py      # FastAPI application
│   └── static/     # PWA Frontend (HTML/JS/Manifest)
├── mcp/            # MCP Tooling
├── db/             # Persistence logic
├── core.py         # Archival Engine
└── cli.py          # Server status & manual CLI
```

## Design Principles

- **Headless First**: UI is a client, not the container.
- **Archival Integrity**: Focus on metadata-rich, persistent storage.
- **Bioluminescent Aesthetic**: Visual identity based on the "StoryTime" gold/void theme.
- **Agentic Native**: Designed to be commanded by AI assistants via MCP.
