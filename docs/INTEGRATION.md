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
| `{stem}.librarian.json` | Capture provenance (url, title, `title_source`, platform, duration, sha256, dates, C-SPAN program/event ids, `asset_url` when the download URL differs from the citable page) |

`.librarian.json` is written by **core.download** (CLI, MCP ingest, multi-program `/event/` expands). Optional extras (e.g. `person_id`) may be merged by callers after download.

`url` is always the page a reader can visit. When the capture came from a CDN
asset, the fetched URL is recorded separately as `asset_url`.

`title_source` says where the title came from, so a derived one is never mistaken
for one the publisher served:

| Value | Meaning |
|-------|---------|
| `publisher` | The extractor or page served this title |
| `operator` | Supplied with `--title` |
| `url-slug` | De-slugged from the publisher's own URL; capitalisation is the slug's |
| `unresolved` | No title could be established; downstream must not cite it |

## Capture identity

A capture whose title is the streaming server's filename (`index`,
`program.674647.tsc`) tells you nothing about what you downloaded, and the URL
stored next to it points at a CDN path rather than a page you can reopen. zget
resolves identity at capture time rather than leaving it to a rename
afterwards, which is how a media file and its sidecar drift apart:

- **C-SPAN behind the WAF**: when neither the API nor the page yields a title,
  it is de-slugged from the program URL, and the filename follows.
- **Raw asset URLs** (`.m3u8`, `.mpd`): refused **before** downloading unless the
  identity can be established, either from `--source-url` or explicitly.

```bash
# A CDN asset with no page: name it, and cite the article it belongs to
uv run zget "https://harvest-media-clips…/index.m3u8" \
  --title "'He's a Bernie Bro': Sen. Collins addresses Troy Jackson" \
  --source-url "https://wgme.com/news/local/hes-a-bernie-bro-…" \
  --channel "WGME"

# The article URL alone is enough when its slug carries the headline
uv run zget "https://harvest-media-clips…/index.m3u8" --source-url "https://wgme.com/news/local/…"
```

`--channel` fills the publisher when a capture reports no uploader; without it,
such captures fall back to the verifiable domain (`wabi.tv`) instead of `NA`.

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
