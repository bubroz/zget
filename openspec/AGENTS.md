# OpenSpec Agent Instructions

These instructions explain how AI assistants should use OpenSpec in this project.

## Project Overview

zget is a high-fidelity TUI and archival engine for video downloads with:

- **1,899 supported extractors** (100% high confidence)
- SQLite-backed library with FTS5 search
- Modern vintage terminal aesthetic

## When to Use OpenSpec

Use OpenSpec when:

- Adding new platform support or extractor features
- Changing the API (download function signature)
- Adding new CLI options
- Major refactoring of core components
- Modifying the registry schema or enrichment pipeline

Skip OpenSpec for:

- Bug fixes and minor patches
- Documentation updates
- Enrichment batch operations
- Small code improvements

## Directory Structure

```
openspec/
├── project.md      # Project context and conventions
├── specs/          # Capability specifications (what zget does)
└── changes/        # Change proposals (what we're adding/changing)
```

## Key Components

| Component | Purpose |
|-----------|---------|
| `core.py` | yt-dlp wrapper and download orchestration |
| `health.py` | Site health monitoring using test URLs |
| `tui/app.py` | Main Textual application |
| `db/store.py` | SQLite operations and FTS5 search |
| `data/enriched_registry.json` | Curated site metadata |

## Creating a Change Proposal

1. Create folder: `openspec/changes/add-<feature>/`
2. Add `proposal.md` with Why/What/Impact
3. Add `tasks.md` with checklist
4. Implement the change
5. Archive when done

## Registry Schema

Each entry in `enriched_registry.json`:

```json
{
  "name": "youtube",
  "description": "YouTube video sharing platform",
  "category": "Social/Community",
  "country": "US",
  "source": "osaurus_search",
  "confidence": "high",
  "test_url": "https://youtube.com/watch?v=...",
  "domain": "youtube.com"
}
```

## Quick Reference

```bash
# Validate specs and changes
npx openspec validate

# Create a new change
mkdir openspec/changes/add-my-feature
```
