<!-- OPENSPEC:START -->
# OpenSpec Instructions: zget (The Archivist)

These instructions are for AI assistants working in this project.

## Mission: The Archival Engine

`zget` is a high-fidelity media archival system built for the Digital Intelligence Ecosystem. It operates as **"The Archivist"**, managing **"The Vault"** (local persistence) and providing **"The Portal"** (PWA discovery).

## Critical Guidelines

- **The Triad**:
  - **The Archivist**: Orchestrates ingestion and format standards (H.264/AAC for universal compatibility).
  - **The Vault**: SQLite-backed local storage for high-fidelity archival.
  - **The Portal**: Premium, **Minimalist** web interface built with native **Custom Elements** and Shadow DOM.
- **Portal Aesthetic**:
  - **Minimalism**: Prioritize content over chrome. Avoid redundant elements (e.g., duplicate descriptions).
  - **High-Density Metadata**: Technical metadata (Views, Codec, Resolution) should be presented cleanly and precisely.
  - **Responsive Context**: Thumbnails must respect **Natural Aspect Ratios** (YouTube vs. Shorts/Reels).
- **Agent Handoff**: `zget` is the primary ingestion pipeline for the ecosystem. Use the MCP `zget_get_local_path` tool to hand off files from **The Vault** to agents like **Librarian**.

Always refer to `openspec/project.md` for full architectural specs.
<!-- OPENSPEC:END -->
