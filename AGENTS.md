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

zget is the local media capture front-end (CLI first, optional web UI, MCP). Downstream tools should not call yt-dlp directly.

**Contract for other projects:** `docs/INTEGRATION.md`

## Key paths

| Path | Role |
|------|------|
| `src/zget/core.py` | download / extract_info |
| `src/zget/platforms/cspan.py` | C-SPAN `/program/` HLS |
| `src/zget/library/paths.py` | path health / rewrite |
| `src/zget/library/ingest.py` | ingest pipeline |
| `src/zget/cli.py` | CLI |
| `src/zget/config.py` | ZGET_HOME and settings |
| `src/zget/server/` | FastAPI + `static/` Web Components |
| `src/zget/mcp/` | MCP server |
| `src/zget/db/` | SQLite |

## Run

```bash
uv sync
uv run zget <url>
uv run zget info <url>
uv run zget --doctor
uv run zget paths check
uv run zget-server --port 9989 --open
uv run pytest
```

## Library rules

- Resolve home: `ZGET_HOME` → `~/.config/zget/config.json` `zget_home` → `~/Downloads/zget`
- Do not hardcode machine-specific library roots in the public repo
- After home or volume renames: `paths rewrite` / `--doctor --fix` before purging
- `--purge-orphans` only for true missing files

## C-SPAN

- `video/?…` native yt-dlp
- `/program/.../{id}` via `platforms/cspan.py`

## Public hygiene

No operator volume names, private corpus paths, or real network IDs in commits.
