<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:

- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:

- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# AI Assistant Instructions: zget

zget is **agentic media capture**: CLI + MCP over yt-dlp. No web UI. Downstream tools must not call yt-dlp directly.

**Contract:** `docs/INTEGRATION.md`

## Key files

| Path | Role |
|------|------|
| `src/zget/core.py` | download / extract_info (writes `.librarian.json`) |
| `src/zget/platforms/cspan.py` | C-SPAN `/program/` + `/event/` HLS |
| `src/zget/metadata/librarian_json.py` | provenance sidecar |
| `src/zget/metadata/nfo.py` | Plex/Jellyfin `.nfo` |
| `src/zget/library/paths.py` | path health / rewrite |
| `src/zget/library/ingest.py` | ingest |
| `src/zget/cli.py` | CLI |
| `src/zget/mcp/` | MCP stdio server |
| `src/zget/db/store.py` | sync SQLite |
| `src/zget/config.py` | ZGET_HOME |

## Run

```bash
uv sync
uv run zget <url>
uv run zget info <url>
uv run zget --doctor
uv run zget paths check
uv run zget-mcp
uv run pytest
```

## Rules

- Home: `ZGET_HOME` → config `zget_home` → `~/Downloads/zget`
- No public commits with operator volume names or private corpus paths
- Path rewrite before orphan purge
- C-SPAN `/program/` and `/event/` supported in-tree (events expand to child programs)
- Every successful download writes `{stem}.librarian.json` (+ CLI/MCP also `.nfo`)
