# zget integration (agents · librarian · Chimera)

zget is the **only capture front-end**. No web UI. Use CLI or MCP.

## Library location

Never hardcode `~/Downloads/zget`. Resolve in order:

1. `ZGET_HOME`
2. `~/.config/zget/config.json` → `zget_home`
3. Fallback: `~/Downloads/zget`

Python (librarian): `librarian.utils.zget_paths.default_zget_home()`.

```bash
cd ~/Projects/zget && uv run zget --stats
cd ~/Projects/zget && uv run zget config show
```

## Capture

```bash
cd ~/Projects/zget
uv run zget "<URL>" --quiet
uv run zget "<URL>" -o /path/to/dir --flat
uv run zget info "<URL>" --json --compact
uv run zget list-channel "<channel-url>" --since 2020-01-01 --jsonl
```

### Sidecars (every successful download)

| File | Role |
|------|------|
| `{stem}.nfo` | Plex/Jellyfin + source URL (`uniqueid type=zget`) |
| `{stem}.librarian.json` | Capture provenance (url, title, platform, duration, sha256, dates, C-SPAN program/event ids) |

`.librarian.json` is written by **core.download** (CLI, MCP ingest, multi-program `/event/` expands). Optional extras (e.g. `person_id`) may be merged by callers after download.

## C-SPAN

| URL | Support |
|-----|---------|
| `c-span.org/video/?…` | yt-dlp |
| `c-span.org/program/.../{id}` | zget HLS resolve + Referer |
| `c-span.org/event/.../{id}` | API → child programs → HLS (speech + presser each download) |

Event pages are containers. Public VOD is on **program** ids (not `event/event.N.m3u8`).
Multi-segment events expand to every child program. If AWS WAF blocks
`/api/events/…`, open c-span.org in a browser once and retry with
`--cookies-from chrome` (needs `aws-waf-token`).

```bash
uv run zget info 'https://www.c-span.org/program/.../NNNNN'
uv run zget 'https://www.c-span.org/program/.../NNNNN' --quiet
uv run zget 'https://www.c-span.org/event/.../NNNNN' --quiet
uv run zget 'https://www.c-span.org/event/.../NNNNN' --cookies-from chrome -o /path/to/dir --flat
```

## Path health

```bash
uv run zget --doctor
uv run zget paths check
uv run zget --doctor --fix           # rewrite only
uv run zget paths rewrite --dry-run
# only after review:
uv run zget --doctor --fix --purge-orphans
```

| Class | Purge? |
|-------|--------|
| healthy / relocatable / off-home | No (fix rewrites relocatable) |
| offline volume | No until remount or sibling rewrite |
| orphan | Only with `--purge-orphans` |

Volume renames: unmounted `/Volumes/Old/rest` can resolve to `/Volumes/New/rest` when that path exists.

## Agents

```bash
uv run zget-mcp
```

Prefer paths from tool results or config, not guessed Downloads paths.

## Invoke pattern for skills

```bash
cd /path/to/zget && uv run zget "URL" --quiet
```

Report the path zget prints (or from `--stats` / search).
