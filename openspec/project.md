# Project Context: zget Archival Engine

## Purpose

`zget` is a high-fidelity media archival system that decouples extraction logic (**The Archivist**) from management (**The Portal** / PWA) and automated integration (MCP).

## Tech Stack

- **FastAPI**: Core server infrastructure (The Archivist).
- **yt-dlp**: Extraction engine (625+ verified, 1,800+ ecosystem).
- **Vanilla JS/CSS**: Premium glassmorphism PWA (The Portal) using **Native Web Components**.
- **SQLite (FTS5)**: Persistence logic (The Vault).
- **MCP**: Model Context Protocol for agentic handoffs.

## Architecture

```
src/zget/
├── server/         # The Portal (FastAPI & Native Components)
├── mcp/            # MCP Tooling
├── db/             # The Vault (Persistence)
├── core.py         # The Archivist (Archival Engine)
└── cli.py          # Server status & manual CLI
```

## Design Principles

- **Framework-Free**: Zero build tools. 100% Native Web Components for The Portal.
- **Minimalist Pivot**: Extreme reduction of UI chrome. Eliminate redundant descriptions; focus on high-fidelity metadata.
- **Natural Context**: Responsive UI that adapts to content aspect ratios (landscape vs. vertical) without cropping.
- **Headless First**: The UI is a client, not the container.
- **Archival Integrity**: Focus on metadata-rich, persistent storage in The Vault.
- **H.264 Standard**: Mandatory H.264/AAC prioritization for seamless cross-platform playback.
- **Agentic Native**: Designed to be commanded by AI assistants via MCP.
