<!-- OPENSPEC:START -->
# OpenSpec Instructions: zget

These instructions are for AI assistants working in this project.

## Mission: The Archival Intelligence Engine

`zget` is a headless archival engine and Webport (PWA) designed for high-fidelity media preservation. It operates as "The Archivist" in the Digital Intelligence Ecosystem.

## Critical Guidelines

- **No TUI**: The terminal UI has been retired. Focus on the FastAPI/PWA core and MCP server.
- **Mobile First**: All UI changes in `src/zget/server/static/index.html` must be mobile-responsive and share-sheet compatible.
- **Agent Integration**: The MCP server (`src/zget/mcp/`) is the primary interface for other agents (Librarian, etc.).

Always refer to `openspec/project.md` for full architectural specs.
<!-- OPENSPEC:END -->
