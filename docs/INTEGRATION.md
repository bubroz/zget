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

## C-SPAN

| URL | Support |
|-----|---------|
| `c-span.org/video/?…` | yt-dlp |
| `c-span.org/program/.../{id}` | zget HLS resolve + Referer |

```bash
uv run zget info 'https://www.c-span.org/program/.../NNNNN'
uv run zget 'https://www.c-span.org/program/.../NNNNN' --quiet
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
