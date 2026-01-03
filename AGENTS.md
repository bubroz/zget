<!-- OPENSPEC:START -->
# OpenSpec Instructions: zget (The Archivist)

These instructions are for AI assistants working in this project.

## Mission: The Museum Pro Archival Engine

`zget` is a high-fidelity media archival system built for the Digital Intelligence Ecosystem. It operates as **"The Archivist"**, managing **"The Vault"** (local persistence) and providing **"The Portal"** (PWA discovery).

## Critical Guidelines

- **No TUI**: The terminal UI has been retired. Focus on the FastAPI/PWA core (`src/zget/server/`) and the MCP server (`src/zget/mcp/`).
- **The Triad**:
  - **The Archivist**: Orchestrates ingestion and format standards (H.264/AAC for universal compatibility).
  - **The Vault**: SQLite-backed local storage for high-fidelity archival.
  - **The Portal**: Premium, glassmorphism-inspired web interface with integrated media playback.
- **Agent Handoff**: `zget` is the primary ingestion pipeline for the ecosystem. Use the MCP `zget_get_local_path` tool to hand off files from **The Vault** to agents like **Librarian**.

Always refer to `openspec/project.md` for full architectural specs.
<!-- OPENSPEC:END -->
